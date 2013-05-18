#! /usr/bin/env python

import datetime
import email
import imaplib
import sys
import time
import keyring
import yaml
import argparse

parser = argparse.ArgumentParser(description='Archive some email.')
parser.add_argument(
	'year',
	type=int,
	help='The year to run the archive on.'
)
args = parser.parse_args()

year = args.year

parameters = None

try:
	with open("parameters.yaml") as parameter_file:
		parameters = yaml.safe_load(parameter_file)
except IOError:
	print "\n\tThe 'parameters.yaml' file does not exist.  Copy the 'parameters.yaml.dist' file to 'parameters.yaml' and configure it appropriately.\n"
	sys.exit()

if parameters is None:
	print "\n\tNo parameters could be read from the 'parameters.yaml' file.  Have you updated it with your configuration?\n"
	sys.exit()

password = keyring.get_password(
	parameters['server'],
	parameters['email']
)

mail = imaplib.IMAP4_SSL(parameters['server'])
mail.login(parameters['email'], password)

mail.select(parameters['folder'])

date = (datetime.date(year, 1, 1) - datetime.timedelta(1)).strftime("%d-%b-%Y")
to_date = (datetime.date(year + 1, 1, 1) - datetime.timedelta(1)).strftime("%d-%b-%Y")
result, data = mail.uid('search', None, '(SINCE {date} BEFORE {to_date})'.format(date=date, to_date=to_date))

uids = data[0].split()

year_hash = {}
uid_count = len(uids)

# find the messages to tuck away and where they should be tucked
for index, uid in enumerate(uids):

	result, data = mail.uid('fetch', uid, '(RFC822)')
	raw_email = data[0][1]

	message = email.message_from_string(raw_email)
	date_string = message['Date']
	date = email.utils.parsedate(date_string)

	year = date[0]
	date_folder = "%s/%02d - %s" % (date[0], date[1], time.strftime('%B', date))

	# so Gmail nests things properly, store the email in both the year and month-specific label
	try:
		year_hash[year].append(uid)
	except KeyError:
		year_hash[year] = [uid]

	try:
		year_hash[date_folder].append(uid)
	except KeyError:
		year_hash[date_folder] = [uid]
	
	if index != 0 and index % 100 == 0:
		print "Processed the %s message of %s..." % (index, uid_count)

# copy the messages to the appropriate folders in bulk
for label, uids in year_hash.items():
	mail.create(label)
	mail.uid('copy', ",".join(uids), label)
