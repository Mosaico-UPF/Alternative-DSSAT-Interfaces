const OUTPUT_FILE_EXT = '.OUT';
const START_HEADER_DELIMITER = '@';
const BLANK_SPACE_DELIMITER = " ";
const EMPTY_DELIMITER = "";

class EvaluateOutput {
    constructor(fs, globalBasePath, cdeInstance) {
        this._fs = fs;
        this._globalBasePath = globalBasePath;
        this._cdeInstance = cdeInstance;
    }

    notEmptyString(value) {
        for (let i = 0; i < value.length; i++) {
            if (value[i] !== " " && value[i]) return true;
        }
        return false;
    }

    getOutFiles(crop) {
        let path = this._globalBasePath + crop;
        let cropFolderContent = this._fs.readdirSync(path);
        let outFiles = [];
        try {
            for (let i = 0; i < cropFolderContent.length; i++) {
                if (cropFolderContent[i].endsWith(OUTPUT_FILE_EXT) && cropFolderContent[i].toLowerCase().includes('evaluate')) {
                    outFiles.push(cropFolderContent[i]);
                }
            }
        } catch (error) {
            console.error('Error reading directory:', error);
        }
        return outFiles;
    }

    read(crop, outFile) {
        let path = this._globalBasePath + crop + "/" + outFile;
        let data;
        try {
            data = this._fs.readFileSync(path, 'utf8');
        } catch (error) {
            console.error(`Error reading file ${path}:`, error);
            return [];
        }

        let lines = data.toString().split(/[\r\n]+/g).filter(line => line.trim() !== '');
        
        let headers = [];
        let results = [];
        const cdeData = this._cdeInstance.load();

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();

            if (line.startsWith('*')) continue;

            if (line.startsWith(START_HEADER_DELIMITER)) {
                // Capture all headers with suffix M or S (measured/simulated)
                const allHeaders = line.split(BLANK_SPACE_DELIMITER)
                    .filter(h => h !== EMPTY_DELIMITER && this.notEmptyString(h))
                    .map(h => h.trim());

                // Include all headers ending in M or S
                headers = allHeaders.filter(header => header.endsWith('M') || header.endsWith('S'));

                // Store indices of filtered headers
                headers.indices = allHeaders
                    .map((h, idx) => ({ header: h, index: idx }))
                    .filter(h => headers.includes(h.header))
                    .map(h => h.index);

                console.log('Detected headers:', headers); // Debug
                continue;
            }

            if (this.notEmptyString(line) && headers.length > 0) {
                let values = line.split(BLANK_SPACE_DELIMITER)
                    .filter(v => v !== EMPTY_DELIMITER && this.notEmptyString(v))
                    .map(v => v.trim());

                // Ensure values align with headers
                if (values.length >= headers.indices[headers.indices.length - 1] + 1) {
                    let record = {};
                    headers.forEach((header, index) => {
                        const valueIndex = headers.indices[index];
                        const rawValue = values[valueIndex];
                        const value = isNaN(rawValue) || rawValue === '-99' ? null : parseFloat(rawValue);

                        const cdeEntry = cdeData.find(cde => cde.cde.trim() === header);
                        const label = cdeEntry ? cdeEntry.label.trim() : header;
                        const description = cdeEntry ? cdeEntry.description.trim() : header;

                        const type = header.endsWith('M') ? 'measured' : header.endsWith('S') ? 'simulated' : 'other';

                        record[label] = {
                            value: value,
                            cde: header,
                            description: description,
                            type: type
                        };
                    });
                    results.push(record);
                }
            }
        }

        return results;
    }
}

module.exports = EvaluateOutput;
