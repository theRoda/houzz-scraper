#!/bin/python
# -*- coding: utf-8 -*-

# houzz scraper
# by: theRoda - thisreallylongname@gmail.com

import re
import csv
import sys
import argparse
import urllib2
from BeautifulSoup import BeautifulSoup
from argparse import ArgumentParser


parser = argparse.ArgumentParser(description='test', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-z', '--zipcode', help='specify ZIP Code.', required=True)
parser.add_argument('-o', '--output', help='specify output filename. default is houzz.csv', nargs='?', default='houzz.csv', type=str)
parser.add_argument('-m', '--miles', help='specify range in miles (10,20,50,100), default is 50.', nargs='?', default=50, type=int)
parser.add_argument('-d', '--depth', help='specify page depth (0-300 recommended). defualt is 5.', nargs='?', default=5, type=int)
parser.add_argument('-s', '--sort', help='specify sort type ((m)ost reviews, (b)est match, (r)ecent reviews). default is recent reviews.', nargs='?', default='r', type=str)
parser.add_argument('-p', '--profession', help='''specify profession. default is architect.
		((a)rchitect, (d)esign-build, (g)eneral-contractor,
		(h)ome-builders, (i)interior-designer, (k)itchen-and-bath, 
		(k)itchen-and-bath-(r)emodeling [kr], (l)andscape-architect, 
		(l)andscape-(c)ontractor [lc], (s)tone-pavers, (t)ile-stone-and-countertop, 
		(all) CAUTION - using 'all' could cause tens of thousands of page requests to be made)''', nargs='?', default='a', type=str)
args = parser.parse_args()


hzbaseurl = 'http://www.houzz.com/professionals'
knownlinks = []

# the goods will end up here
businesslist = []

# translate argument into corresponding URL chunk
def pro(p):
	return {
		'a': 'architect',
		'd': 'design-build',
		'g': 'general-contractor',
		'h': 'home-builders',
		'i': 'interior-designer',
		'k': 'kitchen-and-bath',
		'kr': 'kitchen-and-bath-remodeling',
		'l': 'landscape-architect',
		'lc': 'landscape-contractor',
		's': 'stone-pavers-and-concrete',
		't': 'tile-stone-and-countertop',
		'all': ['architect', 'design-build', 'general-contractor', 'home-builders', 'interior-designer', 'kitchen-and-bath', \
				'kitchen-and-bath-remodeling', 'landscape-architect', 'landscape-contractor', 'stone-pavers-and-concrete', \
				'tile-stone-and-countertop']
	}.get(p, 'architect')
	
# do the same here
def sorttype(s):
	return {
		'm': 'sortReviews',
		'b': 'sortMatch',
		'r': 'sortRecentReviews'
	}.get(s, 'sortMatch')


# nom nom nom
def yumSoup(page, profession):
	zipcode = args.zipcode
	miles = args.miles
	sortby = sorttype(args.sort)
	# create the search URL
	hzsearchurl = '{0}/{1}/c/{2}/d/{3}/{4}/p/{5}'.format(hzbaseurl, profession, zipcode, miles, sortby, page)
	response = urllib2.urlopen(hzsearchurl)
	content = response.read()
	soup = BeautifulSoup(content)
	return soup


# create a list of business details within a list of businesses for later use
# start each business list with it's houzz URL
def getLinks(page, profession):
	soup = yumSoup(page, profession)
	dirtylinks = str(soup.find('script', {'type' : 'application/ld+json'}))
	cleanlinks = re.findall('http[^"]*', dirtylinks)
	for link in cleanlinks:
		if link.startswith('http://www.houzz.com/professionals/') or link.startswith('http://schema.org') or link in knownlinks:
			continue
		knownlinks.append(link)
		newbusinessurl = [link]
		businesslist.append(newbusinessurl)


# fill out info for each business. sends one page request per firm
def buildCards(businesslist):
	for business in businesslist:
		response = urllib2.urlopen(business[0])
		content = response.read()
		soup = BeautifulSoup(content)
		# most of the contact info is here
		contactinfo = soup.findAll('div', {'class' : 'info-list-text'})
		# this is elsewhere
		businessname = str(soup.find('meta', {'name' : 'author'})['content'].encode('utf8'))
		# through testing I have found that any one of these sections can be missing
		# licensenumber and typicalcost are often in each other's section, so we don't explicitly label IndexErrors with section name
		try:
			licensenumber = soup.findAll('div', {'class' : 'info-list-text'})[3].text.encode('utf8')
		except IndexError:
			licensenumber = 'N/A'
		try:
			typicalcost = soup.findAll('div', {'class' : 'info-list-text'})[4].text.encode('utf8')
		except IndexError:
			typicalcost = 'N/A'
		try:
			contactname = str(contactinfo[1].text.encode('utf8'))
		except IndexError:
			contactname = 'Contact:N/A'
		try:
			streetaddress =  str(contactinfo[2].text.encode('utf8'))
		except IndexError:
			streetaddress = 'Location:N/A'
		try:
			phonenumber = str(soup.find('span', {'class' : 'pro-contact-text'}).text.encode('utf8'))
		except AttributeError:
			phonenumber = 'Phone:N/A'
		# there is an edge case where some firms have a website and no phone number, which mangles the phone number section
		# if this is the case, we go find the website elsewhere in the page contents
		if phonenumber == 'Website':
			phonenumber = soup.find('div', {'class' : 'pro-contact-methods one-line'}).a.get('href')
		# populate nested business lists
		business.append(businessname)
		business.append(streetaddress)
		business.append(contactname)
		business.append(phonenumber)
		business.append(licensenumber)
		business.append(typicalcost)
		# show off what we're packaging
		print businessname
		print streetaddress
		print contactname
		print phonenumber
		print licensenumber
		print typicalcost
		print ""
		print ""
		
def writeCSV(outputfile):
	# get it into csv
	with open(outputfile, 'a') as ofile:
		writer = csv.writer(ofile)
		writer.writerow(('URL','Name','Address','Contact','Phone','License','Cost'))
		for business in businesslist:
			writer.writerow((business[0],business[1],business[2],business[3],business[4],business[5],business[6]))
		

def stageOneScraper(profession):
	# the URL page counter increments by 15.
	pagedepth = int(args.depth) * 15
	for page in range(0, pagedepth, 15):
		getLinks(page, profession)


def stageTwoScraper():
	buildCards(businesslist)


def main():
	profession = pro(args.profession)
	if type(profession) is list:
		print 'caution: you have chosen "all". if you have a large page depth set, you might want to get a coffee..'
		for p in profession:
			stageOneScraper(p)
	else:
		stageOneScraper(profession)
	stageTwoScraper()
	outputfile = args.output
	writeCSV(outputfile)
	
	
if __name__ == '__main__':
	main()
