from os import listdir
from os.path import isfile, join
from pathlib import Path
from datetime import datetime
import re, requests, json

outputPath = '../pages/output/'
sectionNames = ["Events", "Births", "Deaths"]
headers = {'content-type': 'application/json'}
files = [f for f in listdir(outputPath) if isfile(join(outputPath, f))]

def processCoordinates(coordinates):
    pairs = re.findall(r'\[(.*?)\]', coordinates)
    coordinatesList = []
    for pair in pairs:
        if pair:
            splitPairs = pair.split(',')
            if len(splitPairs) == 2:
                latitude = splitPairs[0].strip()
                longitude = splitPairs[1].strip()
                if latitude and longitude:
                    coordinatesList.append([float(latitude), float(longitude)])

    return coordinatesList

def processLine(line, year):
    lineArray = line.split(' :;: ')
    if len(lineArray) == 3:
        coordinates = processCoordinates(lineArray[2])
        formattedDate = datetime.strptime(lineArray[0] + ' ' + year, '%B %d %Y').strftime('%Y-%m-%d')
        if formattedDate:
            return {"date": formattedDate, "description": lineArray[1], "coordinates": coordinates}

for file in files:
    with open(outputPath + file) as f:
        section = ""
        for line in f:
            line = line.strip()
            if line in sectionNames:
                section = line
            else:
                newData = processLine(line, file.split('.')[0])
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

                    r = requests.post('http://127.0.0.1:3030/event', data=json.dumps(newEvent), headers=headers)
