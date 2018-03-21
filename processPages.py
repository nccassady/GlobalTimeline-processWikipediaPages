from __future__ import division
from os import listdir
from os.path import isfile, join
from pathlib import Path
from geotext import GeoText
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from pymongo import MongoClient
import codecs, re, time, os
from datetime import datetime, timedelta
from subprocess import call

startScriptTime = datetime.now()
fileProcessingTimes = []

client = MongoClient()
db = client.location_cache
locations = db.locations
people = db.people

inputPath = '../pages/input/'
inputBackupPath = '../pages/input-finished/'
outputPath = '../pages/output/'
personPagePath = '../pages/people/'
logFile = codecs.open('log.txt', mode='a')
files = [f for f in listdir(inputPath) if isfile(join(inputPath, f))]

def writeLog(message):
	print(datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f') + ': ' + message)
	logFile.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f') + ': ' + message + "\n")

def removeLinks(line):
	return re.sub(r'[\[\[]|[\]\]]', '', line)

def formatLine(date, description, location=""):
	return (date + ' :;: ' + description.strip() + " :;: " + location +  "\n")

def getCoordinates(placeName):
	geolocator = Nominatim()
	storedLocation = locations.find_one({'name': placeName})
	location = ['', '']

	if storedLocation:
		writeLog("Location (%s) found in Mongo." % placeName)
		location = storedLocation['coordinates'].split(',')
	elif placeName.strip():
		writeLog("Location (%s) not found, sleeping for 1 second." % placeName)
		try:
			time.sleep(1)
			geocodeLocation = geolocator.geocode(placeName)
		except GeocoderTimedOut as e:
			writeLog("Error thrown getting location: {}.\n\tTrying again.".format(e))
			time.sleep(1)
			geocodeLocation = geolocator.geocode(placeName)

		if geocodeLocation:
			location = [str(geocodeLocation.latitude), str(geocodeLocation.longitude)]
		else:
			writeLog("Unable to find coordinates for (%s)" % placeName)
			return ''
		newLocation = {
			'name': placeName,
			'coordinates': location[0] + ', ' + location[1]
		}
		result = locations.insert_one(newLocation)

	return location[0] + ', ' + location[1]

def getPersonBirthAndDeathCoordinates(name):
	storedPerson = people.find_one({'name': name})
	birthCoordinates = "[]"
	deathCoordinates = "[]"
	if storedPerson:
		writeLog("Person (%s) found in Mongo." % name)
		birthCoordinates = getCoordinates(storedPerson['birthPlace'])
		deathCoordinates = getCoordinates(storedPerson['deathPlace'])
	elif not isfile(personPagePath + name.strip().replace(' ', '_') + '.txt'):
		writeLog("Person (%s) not found." % name)
		call(['python3', 'pywikibot/pwb.py', 'myscript2', name])

		storedPerson = people.find_one({'name': name})
		if storedPerson:
			birthCoordinates = getCoordinates(storedPerson['birthPlace'])
			deathCoordinates = getCoordinates(storedPerson['deathPlace'])
		else:
			writeLog("Person (%s) could not have their birth and death place found." % name)
			return ''
	return '([' + birthCoordinates + '][' + deathCoordinates + '])'

def parseItems(itemList, sectionName):
	outputitems = ""
	unprocessedLines = []

	items = re.findall(r'\*(.*)', itemList.group())
	for item in items:
		itemGroups = re.search(r'^ ?\[\[(.*? \d{1,2})\]\] ?&ndash;(.*)', item)
		if itemGroups:
			date = itemGroups.group(1)
			eventDescription = removeLinks(itemGroups.group(2))

			locationString = ""
			if sectionName == 'Events':
				allPlaces = []
				location = []
				places = GeoText(eventDescription)
				if places.cities:
					allPlaces += places.cities
				if places.countries:
					allPlaces += places.countries

				if allPlaces:
					locationString = '('
					for place in allPlaces:
						coordinates = getCoordinates(place)
						if coordinates not in locationString:
							locationString += '[' + coordinates + ']'

					locationString += ')'
			elif sectionName in ['Births', 'Deaths']:
				personName = re.search(r'(?:(.*?),)', eventDescription)
				if personName:
					locationString = getPersonBirthAndDeathCoordinates(personName.group(1).strip())

			outputitems += formatLine(date, eventDescription, locationString)
		else:
			unprocessedLines.append(item)

	date = ""
	for line in unprocessedLines:
		dateObj = re.search(r'^ \[\[(.* \d{1,2})\]\]', line)
		if dateObj:
			date = dateObj.group(1)
		else:
			itemGroups = re.search(r'\*(.*)', line)

			if itemGroups:
				eventDescription = removeLinks(itemGroups.group(1))
				locationString = ""
				if sectionName == 'Events':
					allPlaces = []
					location = []
					places = GeoText(eventDescription)
					if places.cities:
						allPlaces += places.cities
					if places.countries:
						allPlaces += places.countries

					if allPlaces:
						locationString = '('
						for place in allPlaces:
							coordinates = getCoordinates(place)
							if coordinates not in locationString:
								locationString += '[' + coordinates + ']'
						locationString += ')'

				elif sectionName in ['Births', 'Deaths']:
					personName = re.search(r'(?:(.*?),)', eventDescription)
					if personName:
						locationString = getPersonBirthAndDeathCoordinates(personName.group(1).strip())
				outputitems += formatLine(date, eventDescription, locationString)

	return outputitems

def processSection(name, nextName):
	regexString = '== ?' + name + ' ?==(.*)== ?' + nextName + ' ?=='
	sectionText = re.search(regexString, contents, re.S)
	if sectionText:
		output = parseItems(sectionText, name)
	else:
		output = 'No events found for section: ' + name

	return output

for file in files:
	fileProcessingTime = datetime.now()
	writeLog(file)
	outputFile = codecs.open(outputPath + file, encoding='utf-8', mode='w', errors='replace')
	contents = Path(inputPath + file).read_text()

	outputFile.write("Events\n")
	outputFile.write(processSection('Events', 'Births'))
	outputFile.write("Births\n")
	outputFile.write(processSection('Births', 'Deaths'))
	outputFile.write("Deaths\n")
	outputFile.write(processSection('Deaths', '.*?'))

	outputFile.close()
	os.rename(inputPath + file, inputBackupPath + file)
	fileProcessingTimes.append(datetime.now() - fileProcessingTime)

timeToFinishScript = datetime.now() - startScriptTime
averageTime = (sum(fileProcessingTimes, timedelta()) / len(fileProcessingTimes)).total_seconds()
writeLog("The script took {} seconds to run, processing {} files at an average of {} seconds per file.".format(timeToFinishScript, len(fileProcessingTimes), averageTime))


