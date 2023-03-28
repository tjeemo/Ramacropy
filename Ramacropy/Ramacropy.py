import pickle
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cm
import numpy as np
import sif_parser as sp
import pandas as pd
from Ramacropy.Utils import *




class RamanSpectra():
    def __init__(self, filepath='./PathToFile/Yourfile.csv', laser_wavelength=785.0):
        '''Initialize the Spectra object from a .sif, .pkl or .csv .asc file.

        Important, reads .sif files from Andor. .pkl and .csv files only if generated by THIS SCRIPT,
        or provided from Splitter Script

        Args:
            filepath (str): Path to the .sif file to open. Defaults to './DataFiles/Yourfile.csv'.
            laser_wavelength (float): Wavelength of the laser used in the measurement. Defaults to 785.0 nm.

        Raises:
            ValueError: If the file extension is not '.sif'.

        Returns:
            None
        '''

        # Check if the file exists
        if not os.path.isfile(filepath):
            raise ValueError(f'File {filepath} does not exist.')


        # Load spectral data and information
        self.directory, self.filelab = os.path.split(filepath)
        self.filelab = os.path.splitext(self.filelab)[0]
        self.UID = GenID()
        # Check file extension
        if filepath.endswith('.sif'):
            # Read raw data from sif files
            self.SpectralData, self.SpectralInfo = sp.np_open(filepath)

            # Reshape spectral data for easier plotting
            self.SpectralData = self.SpectralData.transpose(2, 0, 1).reshape(self.SpectralData.shape[2], -1)
            self.RawData = np.copy(self.SpectralData)

            # Extract Raman shift and timestamps from spectral information
            calib = sp.utils.extract_calibration(self.SpectralInfo)
            self.RamanShift = 1E7 * (1 / laser_wavelength - 1 / calib)
            self.TimeStamp = np.arange(0, self.SpectralInfo['CycleTime'] * self.SpectralData.shape[1],
                                       self.SpectralInfo['CycleTime'])

        elif filepath.endswith('.pkl'):
            # Load data from a pickle file
            with open(filepath, 'rb') as file:
                data = pickle.load(file)
                self.RamanShift = data.RamanShift
                self.SpectralData = data.SpectralData
                self.TimeStamp = data.TimeStamp
                self.RawData = data.RawData


        elif filepath.endswith('.csv'):
            #reads the csv, and makes sure that what is not float data is thrown out
            dummy = np.genfromtxt(filepath,delimiter = ';')

            self.TimeStamp = dummy[0, ~np.isnan(dummy[0, :])]

            dummy_less = dummy[2:,~np.isnan(dummy).all(axis = 0)]

            self.RamanShift = dummy_less[:,0]
            self.SpectralData = dummy_less[:,1:]
            self.RawData = np.copy(self.SpectralData)

        elif filepath.endswith('.asc'):
            dummy = pd.read_csv(filepath, sep='\t', decimal='.', skiprows=56, header=None, encoding = 'iso-8859-1')
            dummy = dummy.values
            self.TimeStamp = np.array([0.0])
            self.RamanShift = np.flip(dummy[:,0].reshape((-1)))
            self.SpectralData = np.flip(dummy[:,1].reshape((-1,1)))
            self.RawData = np.copy(self.SpectralData)
        else:
            raise ValueError(f'Sorry, unsupported file type: {filepath}')

    def plot_kinetic(self):
        '''Plot the spectra for a kinetic run.

        Returns:
            None
        '''
        if self.SpectralData.shape[1]==1:
            raise ValueError('This is not a kinetic file, it is a single file. Please use the appropriate function to plot it')
        # Set up colormap and normalization
        cmap = cm.get_cmap('viridis_r')
        norm = colors.Normalize(vmin=self.TimeStamp.min(), vmax=self.TimeStamp.max())
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)

        # Plot the lines with the color array
        fig, ax = plt.subplots()
        for i, t in enumerate(self.TimeStamp):
            ax.plot(self.RamanShift, self.SpectralData[:, i], c=sm.to_rgba(t))

        # Set axis labels and limits
        ax.set_xlabel('Raman Shift (cm$^{-1}$)')
        ax.set_ylabel('Intensity (-)')
        ax.set_xlim(self.RamanShift.min(), self.RamanShift.max())
        ax.set_ylim(0.95 * self.SpectralData.min(), 1.05 * self.SpectralData.max())

        # Add a colorbar to the plot
        sm.set_array([])
        colorbar = plt.colorbar(sm)
        colorbar.set_label('Time (s)')

        # Show the plot
        ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                    textcoords='offset points', ha='left', va='top', color = 'purple', size = 5)
        plt.show()

    def plot_few(self, other_spectra=[], labels=[]):
        '''Plot a single or multiple spectra for comparison.

        Args:
            other_spectra (list): List of other Spectra instances to plot.
            labels (list): List of labels for the spectra. If not provided, filenames are used.

        Raises:
            ValueError: If any of the spectra has more than one column.

        Returns:
            None
        '''
        # Check for single spectrum
        if self.SpectralData.shape[1] != 1:
            raise ValueError('This is not a single spectrum. Use plot_kinetic function instead.')

        # Initialize plot and axis settings
        fig, ax = plt.subplots()
        ax.set_xlabel('Raman Shift (cm$^{-1}$)')
        ax.set_ylabel('Intensity (-)')
        ax.set_xlim(self.RamanShift.min(), self.RamanShift.max())

        # Set up colormap
        num_spectra = len(other_spectra) + 1
        colors = cm.jet(np.linspace(0, 1, num_spectra))

        # Plot spectra
        ax.plot(self.RamanShift, self.SpectralData, c=colors[0], label = self.filelab)
        for i, spec in enumerate(other_spectra):
            if spec.SpectralData.shape[1] != 1:
                raise ValueError('One of the spectra is not a single spectrum. Use PlotKinetic function instead.')
            ax.plot(spec.RamanShift, spec.SpectralData, c=colors[i + 1], label = spec.filelab)

        hand, lab = ax.get_legend_handles_labels()

        if len(labels) > len(lab):
            print('you gave too many labels, your input is ignored!')
        else:
            for i in range(len(labels)):
                lab[i] = labels[i]
        # Set legend and show plot
        ax.legend(hand, lab)
        ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                    textcoords='offset points', ha='left', va='top', color='purple', size=5)
        plt.show()

    def baseline(self, coarsness=0.0, angle=0.0, offset=0.0, interactive=False):
        """
        Corrects the baseline of your spectra. (if the spectra are kinetic uses individual baselines)
        Remember, the baseline brings the spectra to it (i.e. spectra > baseline decreases, baseline > spectra increases)

        Args:
            coarsness (float): Level of similarity between the spectra and the baseline, at 0.0 the baseline is straight,
                at 1.0 the baseline is the same as the spectrum. (lower is better)
            angle (float): What is the angle of the baseline, from -90 to 90. Use this with care.
            offset (float): How high up is the baseline.
            interactive (bool): Whether to show an interactive plot to adjust the baseline parameters (default: False)

        Raises:
            ValueError: If the arguments are out of bounds.

        Returns:
            None
        """
        if coarsness < 0.0 or coarsness > 1.0 or abs(angle) > 90.0:
            raise ValueError("One of your arguments is out of bounds! Try again.")

        if interactive:
            angle, coarsness, offset = InteractiveBline(self.RamanShift, self.SpectralData)
        elif coarsness == 0.0 and angle == 0.0 and offset == 0.0:
            print("Your baseline is all 0s, quit messing around and do something.")
            return

        for count in range(self.SpectralData.shape[1]):
            self.SpectralData[:, count] -= bline(self.RamanShift, self.SpectralData[:, count], coarsness, angle, offset)

    def normalise(self, method='area', interactive=False, **kwargs):
        '''
        normalises the spectra either by the peak or area.
        args:
         method (string): method can be either 'area' or 'peak' the first normalises by area and the second normalises by peak
         interactive (bool): either True or False, if true opens a window in the selected method that you can use to
                            figure out where the bounds of normalisation are
        kwargs: optional (required if interactive is False) keyword arguments to decide the bounds of normalisation
                if method is 'area': the keyword arguments are: start = float and end = float
                if method is 'peak': only one keyword argument is use: peak = float

        :return: nothing
        '''
        if method.lower() not in ['area', 'peak']:
            raise ValueError('Not recognised type of method, either: area or peak')

        if interactive:
            if method.lower() == 'area':
                bounds = InteractiveNormaliseArea(self.RamanShift, self.SpectralData)
                start_pos, end_pos = np.abs(self.RamanShift - bounds[0]).argmin(), np.abs(
                    self.RamanShift - bounds[1]).argmin()
            else:
                peak = InteractiveNormalisePeak(self.RamanShift, self.SpectralData)
                peak_idx = np.abs(self.RamanShift - peak).argmin()
        else:
            if method.lower() == 'area':
                try:
                    bounds = sorted([kwargs['start'], kwargs['end']])
                except KeyError:
                    print('You must have used the wrong keywords, use start and end')
                    return

                if (self.RamanShift.min()<= bounds[1]<= self.RamanShift.max()) and (self.RamanShift.min()<= bounds[1]<= self.RamanShift.max()):
                    start_pos, end_pos = np.abs(self.RamanShift - bounds[0]).argmin(), np.abs(self.RamanShift - bounds[1]).argmin()
                else:
                    raise ValueError('Your chosen start and end area values are out of bounds.')
            else:
                try:
                    peak = kwargs['peak']
                except KeyError:
                    print('You must have used the wrong keyword, use peak')
                    return
                if peak < self.RamanShift.min() or peak > self.RamanShift.max():
                    raise ValueError('The chosen peak position is out of bounds.')
                else:
                    peak_idx = np.abs(self.RamanShift - peak).argmin()

        if method.lower() == 'area':
            for count in range(self.SpectralData.shape[1]):

                self.SpectralData[:, count] = normalise_area(self.SpectralData[:, count], start_pos,end_pos)
        else:
            for count in range(self.SpectralData.shape[1]):
                self.SpectralData[:, count] = normalise_peak(self.SpectralData[:, count], peak_idx)

    def integrate(self, start = 0.0, end = 0.0, interactive = False):
        '''
        integrates the spectrum/spectra and makes a new property of the Specra class called .integral that you can access.
        (works on both kinetic or single spectra)

        :param start: Starting shift of integration
        :param end: ending shift of integration
        :param interactive: Shows plot so you can find this manually
        :return: None
        '''
        if interactive:
            bounds = InteractiveIntegrateArea(self.RamanShift,self.SpectralData)
        else:
            bounds = sorted([start,end])

        if not((self.RamanShift.min() <= bounds[0] <= self.RamanShift.max()) and (self.RamanShift.min() <= bounds[1]<= self.RamanShift.max())):
            raise ValueError('Your chosen start and end values are out of bounds!')

        start_pos,end_pos = np.abs(self.RamanShift - bounds[0]).argmin(), np.abs(self.RamanShift - bounds[1]).argmin()

        self.integral = []
        for count in range(self.SpectralData.shape[1]):
            self.integral.append(integrate_area(self.SpectralData[:,count],start_pos, end_pos))

    def plot_integral_kinetic(self,other_spectra = [], labels = [], conversion = False):
        '''
        Plots a trace of integral over time, or conversion over time. you can optionally add multiple instances of Spectra class
        (integration must have been performed on them) to plot and compare multiple traces. It is suggested to normalise all on the same band

        :param other_spec list of obj: optional other instances of the Spectra class
        :param labels list of str: list of labels to name your traces, if not present uses filenames
        :param conversion bool: If false plots integral, if true plots conversion (calc as 1-I/I0)

        :return: none
        '''
        if self.SpectralData.shape[1] == 1:
            raise ValueError('This is a single spectrum, not really worth it to plot the integral like this'
                             ', better off using the approrpiate function')
        if not(hasattr(self,'integral')):
            raise AttributeError('You need to integrate first before trying to plot it.')

        fig, ax = plt.subplots()
        ax.set_xlabel('Time (s)')

        # Set up colormap
        num_spectra = len(other_spectra) + 1
        colors = cm.jet(np.linspace(0, 1, num_spectra))

        if conversion:
            ax.set_ylabel('Conversion')
            ax.set_ylim(0,1)
            ax.scatter(self.TimeStamp,1 - self.integral/self.integral[0], color = colors[0], label = self.filelab)
        else:
            ax.set_ylabel('Integral')
            ax.scatter(self.TimeStamp,self.integral, color = colors[0], label = self.filelab)

        for i, spec in enumerate(other_spectra):
            if spec.SpectralData.shape[1] == 1:
                raise ValueError('This is a single spectrum, not really worth it to plot the integral like this'
                                 ', better off using the approrpiate function')
            if not (hasattr(spec, 'integral')):
                raise AttributeError('You need to integrate first before trying to plot it.')

            if conversion:
                ax.scatter(spec.TimeStamp,1-spec.integral/spec.integral[0], color = colors[i+1],label = spec.filelab)
            else:
                ax.scatter(spec.TimeStamp,spec.integral, color = colors[i+1], label = spec.filelab)

        hand,lab = ax.get_legend_handles_labels()

        if len(labels)>len(lab):
            print('you gave too many labels, your input is ignored!')
        else:
            for i in range(len(labels)):
                lab[i] = labels[i]
        # Set legend and show plot
        ax.legend(hand,lab)
        ax.set_xlim(0, None)
        ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                    textcoords='offset points', ha='left', va='top', color='purple', size=5)
        plt.show()

    def plot_integral_single(self,other_spectra = [], labels = []):
        '''
        Plots a trace of integral over spectra label. you can optionally add multiple instances of Spectra class
        (integration must have been performed on them) to plot and compare multiple integrals. It is suggested to normalise all on the same band

        :param other_spec list of obj: optional other instances of the Spectra class
        :param labels list of str: list of labels to name your traces, if not present uses filenames

        :return: none
        '''

        if self.SpectralData.shape[1] != 1:
            raise ValueError('This is a kinetic spectrum, not really worth it to plot the integral like this'
                             ', better off using the approrpiate function')
        if not(hasattr(self,'integral')):
            raise AttributeError('You need to integrate first before trying to plot it.')

        fig, ax = plt.subplots()
        fig.subplots_adjust(bottom = 0.2)
        ax.set_ylabel('Integral')


        # Set up colormap
        num_spectra = len(other_spectra) + 1
        colors = cm.jet(np.linspace(0, 1, num_spectra))

        x = np.arange(num_spectra)
        lab = [self.filelab]

        ax.scatter(x[0], self.integral, color = colors[0])

        for i, spec in enumerate(other_spectra):
            if spec.SpectralData.shape[1] != 1:
                raise ValueError('This is a kinetic spectrum, not really worth it to plot the integral like this'
                                 ', better off using the approrpiate function')
            if not (hasattr(spec, 'integral')):
                raise AttributeError('You need to integrate first before trying to plot it.')


            ax.scatter(x[i+1], spec.integral, color=colors[i+1])
            lab.append(spec.filelab)


        if len(labels) > len(lab):
            print('you gave too many labels, your input is ignored!')
        else:
            for i in range(len(labels)):
                lab[i] = labels[i]
        # Set legend and show plot
        ax.set_xticks(x)
        ax.set_xticklabels(lab, rotation = 35)
        ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                    textcoords='offset points', ha='left', va='top', color='purple', size=5)
        plt.show()

    def spike_removal(self):
        '''
        Removes cosmic spikes. BE CAREFUL USING THIS, it may also remove vital information form your spectra!
        Also does not work perfectly, some spikes will remain, You don't need to go and hunt them all anyways so DW
        :return:
        '''

        for count in range(self.SpectralData.shape[1]):
            self.SpectralData[:,count] = savgol_filter(self.SpectralData[:,count], window_length = 5, polyorder = 2)

    def save_changes(self, dirpath = '', filename = ''):
        '''
        Saves the changes you made to your data (in either .pkl or .csv),
        if no place and filename are given it uses the place and filename of the raw data,
        defauls saving method is .pkl. CAREFUL IT OVERWRITES WITHOUT WARNINGS!

        Saving a CSV does not save the raw data if you have made changes. so also be careful with that.
        If you want to save the raw data as well you're recommended to first save as a csv, and then do your changes,
         and save again under a different file name.
        :param dirpath (string): Folder you want to save in example '.\foo\bar\'
        :param filename (string): Name you want to give your file (with extension) example 'HolyHandGrenade.pkl'
        :return: none
        '''
        if dirpath == '':
            dirpath = self.directory
        if filename == '':
            filename = self.filelab+'.pkl'
        if not filename.endswith(('.pkl','.csv')):
            raise ValueError(f'Sorry, filetype {filename[-4:]} not supported, only .pkl or .csv')

        if filename.endswith('.pkl'):
            with open(os.path.join(dirpath,filename),'wb') as file:
                pickle.dump(self,file)

        if filename.endswith('.csv'):
            dummy_saver = np.hstack((self.RamanShift.reshape(-1,1),self.SpectralData))
            dummy_spacer = np.vstack((np.array(['T(s)',*self.TimeStamp]),np.array(['Raman Shift (cm-1)', *np.repeat('counts', self.TimeStamp.shape[0])])))
            dummy_saver = np.vstack((dummy_spacer,dummy_saver))
            np.savetxt(os.path.join(dirpath,filename),dummy_saver,delimiter = ';',fmt = '%s')


class IRSpectra():
    def __init__(self, filepath='./PathToFile/Yourfile.csv'):
        '''Initialize the IR Spectra object from a .txt, .pkl or .csv file.

        Important, reads .pkl and .csv files only if generated by THIS SCRIPT, or .txt files generated from Shimadzu


        Args:
            filepath (str): Path to the .sif file to open. Defaults to './DataFiles/Yourfile.csv'.


        Raises:
            ValueError: If the file extension is not '.sif'.

        Returns:
            None
        '''

        # Check if the file exists
        if not os.path.isfile(filepath):
            raise ValueError(f'File {filepath} does not exist.')

        # Load spectral data and information
        self.directory, self.filelab = os.path.split(filepath)
        self.filelab = os.path.splitext(self.filelab)[0]
        self.UID = GenID()
        # Check file extension
        if filepath.endswith('.txt'):
            #Very inefficient patch to make sure it reads data properly.
            with open(filepath,'r') as file:
                lines = file.readlines()
                if '%T' in lines[3]:
                    self.status = '%T'
                else:
                    self.status = 'Abs'
                if '.' in lines[6]:
                    dec_sep = '.'
                elif ',' in lines[6]:
                    dec_sep = ','
                else:
                    raise ValueError('For some reason this file is neither comma nor decimal separated, WTF?')

            # Read raw data from txt files
            dummy = pd.read_csv(filepath, sep = '\t', decimal = dec_sep, skiprows = 4, header = None)
            dummy = dummy.values

            # Reshape spectral data for easier plotting
            self.SpectralData = dummy[:,1]
            self.RawData = np.copy(self.SpectralData)

            # Extract x axis
            self.Wavenumbers = dummy[:,0]

        elif filepath.endswith('.pkl'):
            # Load data from a pickle file
            with open(filepath, 'rb') as file:
                data = pickle.load(file)
                self.Wavenumbers = data.Wavenumbers
                self.SpectralData = data.SpectralData
                self.RawData = data.RawData
                self.status = data.status


        elif filepath.endswith('.csv'):
            # reads the csv, and makes sure that what is not float data is thrown out
            dummy = np.genfromtxt(filepath, delimiter=',', skip_rows = 1)

            self.Wavenumbers = dummy[:, 0]
            self.SpectralData = dummy[:, 1]
            with open(filepath, 'r') as file:
                first_line = file.readline.strip()

            if '%T' in first_line:
                self.status = '%T'
            elif 'Abs' in first_line:
                self.status = 'Abs'
            else:
                raise ValueError('Have you tampered with the files? y axis is in unknown format')


        else:
            raise ValueError(f'Sorry, unsupported file type: {filepath}')

    def save_changes(self, dirpath = '', filename = ''):
        '''
        Saves the changes you made to your data (in either .pkl or .csv),
        if no place and filename are given it uses the place and filename of the raw data,
        defauls saving method is .pkl. CAREFUL IT OVERWRITES WITHOUT WARNINGS!

        Saving a CSV does not save the raw data if you have made changes. so also be careful with that.
        If you want to save the raw data as well you're recommended to first save as a csv, and then do your changes,
         and save again under a different file name.
        :param dirpath (string): Folder you want to save in example '.\foo\bar\'
        :param filename (string): Name you want to give your file (with extension) example 'HolyHandGrenade.pkl'
        :return: none
        '''
        if dirpath == '':
            dirpath = self.directory
        if filename == '':
            filename = self.filelab+'.pkl'
        if not filename.endswith(('.pkl','.csv')):
            raise ValueError(f'Sorry, filetype {filename[-4:]} not supported, only .pkl or .csv')

        if filename.endswith('.pkl'):
            with open(os.path.join(dirpath,filename),'wb') as file:
                pickle.dump(self,file)

        if filename.endswith('.csv'):
            dummy_saver = np.hstack((self.Wavenumbers.reshape(-1,1),self.SpectralData.reshape(-1,1)))
            dummy_spacer = np.vstack(('Wavenumbers (cm^-1)',self.status)).reshape(-1,2)
            dummy_saver = np.vstack((dummy_spacer,dummy_saver))
            np.savetxt(os.path.join(dirpath,filename),dummy_saver,delimiter = ',',fmt = '%s')

    def t_to_A(self):
        '''
        Transfroms the data from percent Transmission to Absorbacne, it modifies the SpectralData attribute(A = -log(T/100)
        :return:
        '''
        if self.status == '%T':
            self.SpectralData = -np.log10(self.SpectralData / 100)
            self.status = 'Abs'
        else:
            raise ValueError('Data is already in Absorbance')

    def A_to_t(self):
        '''
        Transforms the data from Absorbance to percent Transmission, It modifies SpectralData attribute (T = 100*10^-A)
        :return:
        '''
        if self.status == 'Abs':
            self.SpectralData = 100 * np.power(10, -self.SpectralData)
            self.status = '%T'
        else:
            raise ValueError('Data is already in Transmission')

    def plot_few(self, other_spectra=[], labels=[]):
        '''Plot a single or multiple spectra for comparison.

        Args:
            other_spectra (list): List of other Spectra instances to plot.
            labels (list): List of labels for the spectra. If not provided, filenames are used.

        Raises:
            ValueError: If any of the spectra has more than one column.

        Returns:
            None
        '''


        # Initialize plot and axis settings
        fig, ax = plt.subplots()
        ax.set_xlabel('Wavenumber (cm$^{-1}$)')
        if self.status == '%T':
            ax.set_ylabel('Transmission %')
        else:
            ax.set_ylabel('Absorbance')

        ax.set_xlim(self.Wavenumbers.min(), self.Wavenumbers.max())

        # Set up colormap
        num_spectra = len(other_spectra) + 1
        colors = cm.jet(np.linspace(0, 1, num_spectra))

        # Plot spectra
        ax.plot(self.Wavenumbers, self.SpectralData, c=colors[0], label = self.filelab)
        for i, spec in enumerate(other_spectra):
            if spec.status != self.status:
                raise ValueError('Does not make much sense to plot Transmission and Absorbances toghether...')
            ax.plot(spec.Wavenumbers, spec.SpectralData, c=colors[i + 1], label = spec.filelab)

        hand, lab = ax.get_legend_handles_labels()

        if len(labels) > len(lab):
            print('you gave too many labels, your input is ignored!')
        else:
            for i in range(len(labels)):
                lab[i] = labels[i]
        # Set legend and show plot
        if self.status == '%T':
            ax.set_ylim(None,100)
            ax.annotate(self.UID[:8], xy=(0, 0.05), xytext=(5, -5), xycoords='axes fraction',
                        textcoords='offset points', ha='left', va='top', color='purple', size=5)
        else:
            ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                        textcoords='offset points', ha='left', va='top', color='purple', size=5)
        ax.legend(hand, lab)
        ax.invert_xaxis()
        plt.show()

    def baseline(self, coarsness=0.0, angle=0.0, offset=0.0, interactive=False):
        """
        Corrects the baseline of your spectra. (if the spectra are kinetic uses individual baselines)
        Remember, the baseline brings the spectra to it (i.e. spectra > baseline decreases, baseline > spectra increases)

        Args:
            coarsness (float): Level of similarity between the spectra and the baseline, at 0.0 the baseline is straight,
                at 1.0 the baseline is the same as the spectrum. (lower is better)
            angle (float): What is the angle of the baseline, from -90 to 90. Use this with care.
            offset (float): How high up is the baseline.
            interactive (bool): Whether to show an interactive plot to adjust the baseline parameters (default: False)

        Raises:
            ValueError: If the arguments are out of bounds.

        Returns:
            None
        """
        if coarsness < 0.0 or coarsness > 1.0 or abs(angle) > 90.0:
            raise ValueError("One of your arguments is out of bounds! Try again.")
        if self.status == '%T':
            return ValueError('Convert to Absorbance before applying a baseline')

        if interactive:
            angle, coarsness, offset = InteractiveBlineIR(self.Wavenumbers, self.SpectralData)
        elif coarsness == 0.0 and angle == 0.0 and offset == 0.0:
            raise ValueError('Quit playing around, your baseline is empty')



        self.SpectralData -= bline(self.Wavenumbers, self.SpectralData, coarsness, angle, offset)

    def integrate(self, start = 0.0, end = 0.0, interactive = False):
        '''
        integrates the spectrum/spectra and makes a new property of the Specra class called .integral that you can access.
        (works on both kinetic or single spectra)

        :param start: Starting shift of integration
        :param end: ending shift of integration
        :param interactive: Shows plot so you can find this manually
        :return: None
        '''
        if self.status != 'Abs':
            raise ValueError('Operation can only be performed in Absorbance')

        if interactive:
            bounds = InteractiveIntegrateAreaIR(self.Wavenumbers,self.SpectralData)
        else:
            bounds = sorted([start,end])

        if not((self.Wavenumbers.min() <= bounds[0] <= self.Wavenumbers.max()) and (self.Wavenumbers.min() <= bounds[1]<= self.Wavenumbers.max())):
            raise ValueError('Your chosen start and end values are out of bounds!')

        start_pos,end_pos = np.abs(self.Wavenumbers - bounds[0]).argmin(), np.abs(self.Wavenumbers - bounds[1]).argmin()

        self.integral = integrate_area(self.SpectralData,start_pos, end_pos)

    def spec_pos_val(self, position = 0.0, interactive=False):
        '''
        saves the value of the spectrum at position position
        args:
         method (float): position of the data to read (wavenumbers)
         interactive (bool): either True or False, if true opens a window in the selected method that you can use to
                            figure out where the bounds of normalisation are


        :return: nothing
        '''
        if self.status != 'Abs':
            raise ValueError('Operation can only be performed with Absorbance')

        if interactive:
            self.peak = InteractivePeakPositionIR(self.Wavenumbers, self.SpectralData)

        else:
            if self.Wavenumbers.min()<=position<=self.Wavenumbers.max():
                peak_idx = np.abs(self.Wavenumbers - position).argmin()
                self.peak = self.SpectralData[peak_idx]
            else:
                raise ValueError('The chosen peak position is out of bounds.')

    def plot_values_single(self, other_spectra = [], labels = [], method = 'integral'):
        '''
        Plots a trace of integral (or position at x) over spectra label. you can optionally add multiple instances of Spectra class
        (integration must have been performed on them) to plot and compare multiple integrals. It is suggested to normalise all on the same band

        :param other_spec list of obj: optional other instances of the Spectra class
        :param labels list of str: list of labels to name your traces, if not present uses filenames
        :param calibration_curve bool: if true it will attempt to make a linear interpolation between the 'other_spectra' assumed
        that you have given the not acetylated and 85% acetylated starch with the pos_val at the right peak for all three.

        :return: none
        '''

        if method.lower() not in ['integral','peak']:
            raise ValueError('Method not supported, use either: integral or peak')
        if not(hasattr(self,'integral')) and method.lower() == 'integral':
            raise AttributeError('You need to integrate first before trying to plot it.')
        elif not(hasattr(self,'peak')) and method.lower() == 'peak':
            raise AttributeError('You need to measure a peak position first')


        fig, ax = plt.subplots()
        fig.subplots_adjust(bottom=0.2)

        # Set up colormap
        num_spectra = len(other_spectra) + 1
        colors = cm.jet(np.linspace(0, 1, num_spectra))

        x = np.arange(num_spectra)
        lab = [self.filelab]
        if method.lower() =='integral':
            ax.scatter(x[0], self.integral, color = colors[0])
        else:
            ax.scatter(x[0],self.peak,color = colors[0])

        for i, spec in enumerate(other_spectra):
            if not (hasattr(self, 'integral')) and method.lower() == 'integral':
                raise AttributeError('You need to integrate first before trying to plot it.')
            elif not (hasattr(self, 'peak')) and method.lower() == 'peak':
                raise AttributeError('You need to measure a peak position first')
            if spec.status != self.status:
                raise ValueError('Not possible to plot spectra in Absorbance and spectra in Transmission at the same time')

            if method.lower() == 'integral':
                ax.scatter(x[i+1], spec.integral, color=colors[i+1])
            else:
                ax.scatter(x[i+1], spec.peak, color=colors[i+1])

            lab.append(spec.filelab)

        if len(labels) > len(lab):
            print('you gave too many labels, your input is ignored!')
        else:
            for i in range(len(labels)):
                lab[i] = labels[i]
        # Set legend and show plot
        ax.set_ylabel(None,None)
        ax.set_xticks(x)
        ax.set_xticklabels(lab, rotation = 35)
        if method.lower() == 'integral':
            ax.set_ylabel('Integral')
        elif self.status == 'Abs':
            ax.set_ylabel('Absorbance Value')
        elif self.status == '%T':
            ax.set_ylabel('Transmittance Value')
        ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                    textcoords='offset points', ha='left', va='top', color='purple', size=5)
        plt.show()

    def plot_calibration(self, acetyl_0 = None, acetyl_85 = None, starch_b = None, starch_c = None):
        '''Plots a calibration curve between not acetylated and 85% acetylated starch and finds out where your sample is.
         Important to notice that you sample, acetyl_0 and acetyl_85 all need to be in absorbance mode, with the peak position at the right
         wavenumbers calculated (with spec_pos_val) (you need to figure out wich position that is

         :param acetyl_0 IRspectra class: IR spectrum class of the non acetylated starch from AVEBE
         :param acetyl_85 IRspectra class: IR spectrum class of the 85% acetylated starch from AVEBE

         :return none'''


        if acetyl_85 == None or acetyl_0 == None:
            raise ValueError('Your reference values are missing')

        elif (acetyl_0.status =='%T' or acetyl_85.status == '%T') or self.status == '%T':
            raise ValueError('One of the spectra is in transmission, not allowed (you get log_10 calibration curves)')
        elif (not(hasattr(acetyl_85, 'peak'))) or (not(hasattr(acetyl_0,'peak'))):
            raise AttributeError('No peak found on one of the reference spectra')

        if starch_b == None or starch_c == None:
            print(f'you are not plotting all the data you should, however this is fine, just letting you know')
        elif starch_c.status == '%T' or starch_b.status == '%T':
            raise ValueError('one of your data sets is still in transmission, not allowed')
        elif (not(hasattr(starch_b,'peak'))) or (not(hasattr(starch_c,'peak'))):
            raise AttributeError('No peak found for one of the other spectra')

        cal_slope, cal_icept = np.polyfit([0,0.85],[acetyl_0.peak,acetyl_85.peak],1)
        numb_spec = 3
        if not(starch_b is None):
            numb_spec +=1
        if not(starch_c is None):
            numb_spec +=1

        colors = cm.jet(np.linspace(0, 1,numb_spec))
        fig,ax = plt.subplots()

        ax.set_xlabel('Acetylation Fraction')
        ax.set_ylabel('Absorption')

        x_trend = np.linspace(0,1,100)
        y_trend = cal_slope*x_trend+cal_icept

        ax.plot(x_trend,y_trend,color = 'red', linestyle = '--')

        x_points = [0,0.85,(self.peak-cal_icept)/cal_slope]
        y_points = [acetyl_0.peak, acetyl_85.peak,self.peak]
        labels = [f'Calibration line:{cal_slope:.2f}*Af +{cal_icept:.2f}','0% Acetylated',
                   '85% Acetylated', f'Starch_A (x val = {x_points[2]:.2f})']
        if not(starch_c is None):
            x_points.append((starch_c.peak-cal_icept)/cal_slope)
            y_points.append(starch_c.peak)
            labels.append(f'Starch_C (x val = {x_points[-1]:.2f})')
        if not(starch_b is None):
            x_points.append((starch_b.peak - cal_icept) / cal_slope)
            y_points.append(starch_b.peak)
            labels.append(f'Starch_B (x val = {x_points[-1]:.2f})')
        for i,x in enumerate(x_points):
            ax.scatter(x,y_points[i], color = colors[i])


        ax.legend(labels)
        ax.annotate(self.UID[:8], xy=(0, 1), xytext=(5, -5), xycoords='axes fraction',
                    textcoords='offset points', ha='left', va='top', color='purple', size=5)
        ax.set_xlim(0, None)
        plt.show()

    def normalise_peak(self, peak_wn = 0.0, interactive=False):
        '''
        normalises the spectra either by the value of absorbance at the selected peak.
        args:
         peak_wn: wavenumbers of peak to be normalised (required only if interactive is false)
         interactive (bool): either True or False, if true opens a window in the selected method that you can use to
                            figure out where the bounds of normalisation are


        :return: nothing
        '''
        if self.status == '%T':
            raise ValueError('This operation is only available in absorbance mode')
        if interactive:
            peak = InteractiveNormalisePeakIR(self.Wavenumbers, self.SpectralData)
            peak_idx = np.abs(self.Wavenumbers - peak).argmin()
        else:
            if peak_wn == 0.0:
                raise ValueError('Peak_wn parameter not given')
            elif peak_wn <= self.Wavenumbers.min() or peak_wn >= self.Wavenumbers.max():
                raise ValueError('Peak_wn out of borders')
            else:
                peak_idx = np.abs(self.Wavenumbers - peak_wn).argmin()


        self.SpectralData = normalise_peak(self.SpectralData, peak_idx)