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
# @todo add the default days to process to the config file
# @todo add shortcuts for the last 30 and 365 days
parser.add_argument(
	'--days-to-process',
	type=int,
	default="1",
	help='Archive the last X days worth of mail.  Defaults to 1.'
)
parser.add_argument(
	'--parameter-file',
	type=str,
	default="parameters.yaml",
	help='The file containing the configured parameters. Defaults to "parameters.yaml".'
)
args = parser.parse_args()

days_to_process = args.days_to_process
parameter_file_name = args.parameter_file

parameters = None

try:
	with open(parameter_file_name) as parameter_file:
		parameters = yaml.safe_load(parameter_file)

except IOError:
	print "\nERROR:  The '%s' file does not exist.  Copy the 'parameters.yaml.dist' file to '%s' and configure it appropriately.\n" % (parameter_file_name, parameter_file_name)
	parser.print_help()
	sys.exit()

if parameters is None:
	print "\nERROR:  No parameters could be read from the 'parameters.yaml' file.  Have you updated it with your configuration?\n"
	parser.print_help()
	sys.exit()

password = keyring.get_password(
	parameters['server'],
	parameters['email']
)

mail = imaplib.IMAP4_SSL(parameters['server'])
mail.login(parameters['email'], password)

mail.select(parameters['folder'])

from_date = (datetime.date.today() - datetime.timedelta(days_to_process)).strftime("%d-%b-%Y")
to_date = (datetime.date.today()).strftime("%d-%b-%Y")

result, data = mail.uid('search', None, '(SINCE {from_date} BEFORE {to_date})'.format(from_date=from_date, to_date=to_date))

uids = data[0].split()

year_hash = {}
uid_count = len(uids)

# find the messages to tuck away and where they should be tucked
for index, uid in enumerate(uids):

	result, data = mail.uid('fetch', uid, '(RFC822.HEADER)')
	raw_email = data[0][1]

	message = email.message_from_string(raw_email)
	date_string = message['Date']
	date = email.utils.parsedate(date_string)

	# ok, there's no Date header--try faking one from the Received
	if date is None and message.has_key('Received') and message['Received'] is not None:
		date = email.utils.parsedate(message['Received'].split(";")[1])

	# ok, something wasn't parsed right.  Try it manually.
	if date is None:
		lines = raw_email.split("\n")
		for line in lines:
			if line.startswith("Date:"):
				# so I *do* have a Date header--nice!
				date = email.utils.parsedate(line.split(": ")[1])
				if date is not None:
					break

	if date is not None:
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
	else:
		print "Unparsable date string: '%s'" % date_string
		print message
		sys.exit()


# copy the messages to the appropriate folders in bulk
for label, uids in year_hash.items():
	mail.create(label)
	mail.uid('copy', ",".join(uids), label)
