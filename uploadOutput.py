from os import listdir
from os.path import isfile, join
from pathlib import Path
from datetime import datetime
import re, requests, json

outputPath = '../pages/output/'
sectionNames = ["Events", "Births", "Deaths"]
headers = {'content-type': 'application/json'}
# files = [f for f in listdir(inputPath) if isfile(join(inputPath, f))]

# for file in files:
    # fileProcessingTime = datetime.now()
    # print(file)
    # logFile.write(file)
    # logFile.write("\n")
    # outputFile = codecs.open(outputPath + file, encoding='utf-8', mode='w', errors='replace')
    # contents = Path(inputPath + file).read_text()

    # "name": "Test 1",
    # "date": {
    #     "$date": "2016-01-01T05:00:00.000Z"
    # },
    # "description": "Description",
    # "latitude": 35.585,
    # "longitude": -77.37,
    # "category": "Other"
# February 6 :;: The International Arbitration Court at The Hague is created, when the Netherlands' Senate ratifies an 1899 peace conference decree. :;: ([-33.9583333,  18.6416667][52.2379891,  5.53460738161551])
# February 8 :;: Second Boer War: British troops are defeated by the Boers at Ladysmith, South Africa|Ladysmith. :;: ([-28.8166236,  24.991639])

def processCoordinates(coordinates):
    pairs = re.findall(r'\[(.*?)\]', coordinates)
    coordinatesList = []
    for pair in pairs:
        if pair:
            splitPairs = pair.split(',')
            coordinatesList.append([float(splitPairs[0].strip()), float(splitPairs[1].strip())])
    return coordinatesList

def processLine(line, year):
    lineArray = line.split(' :;: ')
    if len(lineArray) == 3:
        coordinates = processCoordinates(lineArray[2])
        formattedDate = datetime.strptime(lineArray[0] + ' ' + year, '%B %d %Y').strftime('%Y-%m-%d')
        if formattedDate:
            return {"date": formattedDate, "description": lineArray[1], "coordinates": coordinates}

count = 0
with open(outputPath + '1900.txt') as f:
    section = ""
    for line in f:
        line = line.strip()
        if line in sectionNames:
            section = line
        else:
            newData = processLine(line, '1900')
            if newData:
                if section == 'Events':
                    for pair in newData["coordinates"]:
                        newEvent = {
                            "description": newData["description"],
                            "latitude": pair[0],
                            "longitude": pair[1],
                            "date": newData["date"],
                            "category": "Event"
                        }
                elif section == "Births":
                    if newData["coordinates"]:
                        newEvent = {
                            "name": newData["description"].split(',')[0],
                            "description": newData["description"].split(',')[1],
                            "latitude": newData["coordinates"][0][0],
                            "longitude": newData["coordinates"][0][1],
                            "date": newData["date"],
                            "category": "Birth"
                        }
                elif section == "Deaths":
                    if len(newData["coordinates"]) == 2:
                        newEvent = {
                            "name": newData["description"].split(',')[0],
                            "description": newData["description"].split(',')[1],
                            "latitude": newData["coordinates"][1][0],
                            "longitude": newData["coordinates"][1][1],
                            "date": newData["date"],
                            "category": "Death"
                        }
                if count < 3:
                    count = count+1
                    r = requests.post('http://127.0.0.1:3030/event', data=json.dumps(newEvent), headers=headers)
