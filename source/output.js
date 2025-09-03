const OUTPUT_FILE_EXT = '.OUT';
const TREATMENT_DELIMITER = 'TREATMENT';
const MODEL_DELIMITER = 'MODEL';
const EXPERIMENT_DELIMITER = 'EXPERIMENT';
const DATA_PATH_DELIMITER = 'DATA PATH';
const START_HEADER_DELIMITER = '@';
const BLANK_SPACE_DELIMITER = " ";
const EMPTY_DELIMITER = "";
const { convertToISODate } = require('./utils');

class Output {
    constructor(fs) {
        this._fs = fs;
    }

    notEmptyString(value) {
      for (let i = 0; i < value.length; i++) {
        if (value[i] !== " " && value[i]) return true;
      }
      return false;
    }

    getOutFiles(globalBasePath, delimiterPath, cropSelected) {
        let path = globalBasePath + delimiterPath + cropSelected;
        let cropFolderContent = this._fs.readdirSync(path);
        let outFiles = [];
        try {
            for (let i = 0; i < cropFolderContent.length; i++) {
                let isOutFile = cropFolderContent[i].endsWith(OUTPUT_FILE_EXT);

                if (isOutFile) {
                    outFiles.push(cropFolderContent[i]);
                }
            }
        } catch (error) {
            console.log(error);
        } finally {
            return outFiles;
        }
    }
    
    read(globalBasePath, crop, outFile) {
        let path = globalBasePath + crop + "//" + outFile;
        let data = this._fs.readFileSync(path);
        let lines = data.toString().split(/[\r\n]+/g);
        let headers = [];
        let experiments = [];
        let result = [];
        let experiment = "";
        let treatmentDescription = "";

        for (let i = 0; i < lines.length; i++) {
          if (lines[i].startsWith(' EXPERIMENT')) {
            experiment = lines[i].substring(18, lines[i].length).split(' ')[0];
          }

          if (lines[i].startsWith(' TREATMENT')) {
            let run = lines[i].split(':');
            let treatmentNumber = run[0];
            treatmentDescription = run[1];
            let treatment = treatmentNumber.replace(TREATMENT_DELIMITER, EMPTY_DELIMITER).trim();

            if (!result.find(item => item.run === treatmentDescription.trim())) {
              let model = { run: treatmentDescription.trim(), experiment: experiment, treatmentNumber: treatment, values: [] };
              result.push(model);
            }
            experiments = [];
            continue;
          }

          if (lines[i].startsWith(START_HEADER_DELIMITER)) {
            headers = lines[i].slice(1).trim().split(BLANK_SPACE_DELIMITER).filter(h => h !== EMPTY_DELIMITER);
            continue;
          }

          if (lines[i].startsWith(BLANK_SPACE_DELIMITER) &&
              this.notEmptyString(lines[i]) &&
              !lines[i].includes(MODEL_DELIMITER) &&
              !lines[i].includes(EXPERIMENT_DELIMITER) &&
              !lines[i].includes(DATA_PATH_DELIMITER) &&
              !lines[i].includes(TREATMENT_DELIMITER)) {
            let simulationValues = lines[i].substring(1).trim();
            let simulationValuesArray = simulationValues.split(BLANK_SPACE_DELIMITER).filter(v => v !== EMPTY_DELIMITER);

            let index = 0;
            for (let k = 0; k < simulationValuesArray.length && index < headers.length; k++) {
              let values = [simulationValuesArray[k]];
              let obj = { cde: headers[index], values: values };
              if (experiments[index]) {
                experiments[index].values.push(simulationValuesArray[k]);
              } else {
                experiments.push(obj);
              }
              index++;
            }
            result[result.length - 1].values = experiments;
          }
        }

        // Transform to unified format
        let unifiedResult = [];
        for (const model of result) {
            const unified = {
              run: model.run,
              treatmentNumber: model.treatmentNumber,
              experiment: model.experiment,
              fileType: 'OUT',
              simulated: {},
              measuredFinal: {},
              measuredTimeSeries: {}
            };
            const dates = [];
            const yearIndex = model.values.findIndex(v => v.cde === 'YEAR');
            const doyIndex = model.values.findIndex(v => v.cde === 'DOY');
            if (yearIndex !== -1 && doyIndex !== -1) {
                const years = model.values[yearIndex].values;
                const doys = model.values[doyIndex].values;
                for (let dayIdx = 0; dayIdx < Math.min(years.length, doys.length); dayIdx++) {
                  const date = convertToISODate(years[dayIdx], doys[dayIdx]);
                  dates.push(date || `index-${dayIdx}`); // Fallback if date invalid
                }
            } else {
                // Fallback: Use index-based "dates" if YEAR/DOY missing
                const maxLength = Math.max(...model.values.map(v => v.values.length));
                for (let i = 0; i < maxLength; i++) {
                  dates.push(`index-${i}`);
                }
            }
            model.values.forEach(varObj => {
              if (['YEAR', 'DOY', 'DAS', 'DAP'].includes(varObj.cde)) return;
              unified.simulated[varObj.cde] = {
                values: varObj.values.map(v => isNaN(parseFloat(v)) ? v : parseFloat(v)),
                dates
              };
            });
            unifiedResult.push(unified);
        }
        return unifiedResult;
    }
}

module.exports = Output;