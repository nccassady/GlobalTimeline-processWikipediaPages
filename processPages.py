from __future__ import division
from os import listdir
from os.path import isfile, join
from pathlib import Path
from geotext import GeoText
from geopy.geocoders import Nominatim
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
logFile = codecs.open('log.txt', mode='w')
files = [f for f in listdir(inputPath) if isfile(join(inputPath, f))]

def removeLinks(line):
	return re.sub(r'[\[\[]|[\]\]]', '', line)

def formatLine(date, description, location=""):
	return (date + ' :;: ' + description.strip() + " :;: " + location +  "\n")

def getCoordinates(placeName):
	geolocator = Nominatim()
	storedLocation = locations.find_one({'name': placeName})

	if storedLocation:
		print("Location (%s) found in Mongo." % placeName)
		logFile.write("Location (%s) found in Mongo." % placeName)
		logFile.write("\n")
		location = storedLocation['coordinates'].split(',')
	else:
		print("Location (%s) not found, sleeping for 1 second." % placeName)
		logFile.write("Location (%s) not found, sleeping for 1 second." % placeName)
		logFile.write("\n")
		time.sleep(1)
		geocodeLocation = geolocator.geocode(placeName)
		if geocodeLocation:
			location = [str(geocodeLocation.latitude), str(geocodeLocation.longitude)]
		else:
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
		print("Person (%s) found in Mongo." % name)
		logFile.write("Person (%s) found in Mongo." % name)
		logFile.write("\n")
		birthCoordinates = getCoordinates(storedPerson['birthPlace'])
		deathCoordinates = getCoordinates(storedPerson['deathPlace'])
	else:
		print("Person (%s) not found." % name)
		logFile.write("Person (%s) not found." % name)
		logFile.write("\n")
		call(['python3', 'pywikibot/pwb.py', 'myscript2', name])

		storedPerson = people.find_one({'name': name})
		if storedPerson:
			birthCoordinates = getCoordinates(storedPerson['birthPlace'])
			deathCoordinates = getCoordinates(storedPerson['deathPlace'])
		else:
			print("Person (%s) could not have their birth and death place found." % name)
			logFile.write("Person (%s) could not have their birth and death place found." % name)
			logFile.write("\n")
			return ''
	return '(' + birthCoordinates + deathCoordinates + ')'

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
	print(file)
	logFile.write(file)
	logFile.write("\n")
	outputFile = codecs.open(outputPath + file, encoding='utf-8', mode='w', errors='replace')
	contents = Path(inputPath + file).read_text()

	outputFile.write("Events\n")
	outputFile.write(processSection('Events', 'Births'))
	outputFile.write("Births\n")
	outputFile.write(processSection('Births', 'Deaths'))
	outputFile.write("Deaths\n")
	outputFile.write(processSection('Deaths', '.*?'))

	# eventsText = re.search(r'== Events ==(.*)== Births ==', contents, re.S)
	# if eventsText:
	# 	events = parseItems(eventsText)
	# 	outputFile.write(events)
	# else:
	# 	print 'No events found'

	# births = re.search(r'== Births ==(.*)== Deaths ==', contents, re.S)
	# if births:
	# 	births = parseItems(births)
	# 	outputFile.write(births)
	# else:
	# 	print 'No births found'

	outputFile.close()
	os.rename(inputPath + file, inputBackupPath + file)
	fileProcessingTimes.append(datetime.now() - fileProcessingTime)

timeToFinishScript = datetime.now() - startScriptTime
averageTime = (sum(fileProcessingTimes, timedelta()) / len(fileProcessingTimes)).total_seconds()
print("The script took {} seconds to run, processing {} files at an average of {} seconds per file.".format(timeToFinishScript, len(fileProcessingTimes), averageTime))


