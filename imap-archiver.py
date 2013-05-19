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
parser.add_argument(
	'--month',
	type=int,
	default="13",
	help='The month to run the archive on. Optional, defaults to all months.'
)
parser.add_argument(
	'--parameter_file',
	type=str,
	default="parameters.yaml",
	help='The file containing the configured parameters. Defaults to "parameters.yaml".'
)
args = parser.parse_args()

year = args.year
month = args.month
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

date = (datetime.date(year, 1, 1) - datetime.timedelta(1)).strftime("%d-%b-%Y")
to_date = (datetime.date(year + 1, 1, 1) - datetime.timedelta(1)).strftime("%d-%b-%Y")
if month < 13:
	date = (datetime.date(year, month, 1) - datetime.timedelta(1)).strftime("%d-%b-%Y")
	if month != 12:
		to_date = (datetime.date(year, month + 1, 2) - datetime.timedelta(1)).strftime("%d-%b-%Y")
	else:
		to_date = (datetime.date(year + 1, 1, 2) - datetime.timedelta(1)).strftime("%d-%b-%Y")


print '(SINCE {date} BEFORE {to_date})'.format(date=date, to_date=to_date)
result, data = mail.uid('search', None, '(SINCE {date} BEFORE {to_date})'.format(date=date, to_date=to_date))

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
