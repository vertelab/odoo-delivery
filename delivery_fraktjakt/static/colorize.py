#!/usr/bin/python

import os
import time
import requests
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

dimensions_file = raw_input(color.RED + "Do you wish to upload a file containing the packet dimensions? (yes/no)" + color.END + "\n\r" + ">> ")
if dimensions_file == "no":
	vikt = raw_input("How much does the packet weigh (kg)?" + "\n\r" + ">> ")
	langd = raw_input("What is the lenght of the packet (cm)?" + "\n\r" + ">> ")
	bredd = raw_input("What is the width of the packet (cm)?" + "\n\r" + ">> ")
	hojd = raw_input("What is the height of the packet (cm)?" + "\n\r" + ">> ")

	print("Looking up prices...")

elif dimensions_file == "yes":
	print("\n\r" + color.GREEN + "Place a text file in the same folder as the script and call it" + color.END + color.BOLD + " lev.txt " + color.END + color.GREEN + "with the following format:" + color.END + "\n\r" + "vikt <siffra i kg>" + "\n\r" + "langd <siffra i cm>" + "\n\r" + "bredd <siffra i cm>" + "\n\r" + "hojd <siffra i cm>")
	print("address <leveransadress + siffra>" + "\n\r" + "postkod <postnr>" + "\n\r" + "land <forkortning pa 2st bokstaver ex: SE>" + "\n\r")
	
	filename = 'lev.txt'
	file_content = {}
	with open(filename) as file_object:
		for line in file_object:
			tok = line.split()
			file_content[tok[0]] = tok[1]
		#print(file_content)

	vikt = file_content.get('vikt')
	langd = file_content.get('langd')
	bredd = file_content.get('bredd')
	hojd = file_content.get('hojd')

	print(color.GREEN + "You have provided the following details:" + color.END)
	print("vikt " + vikt + "\n\r" + "langd " + langd + "\n\r" + "bredd " + bredd + "\n\r" + "hojd " + hojd + "\n\r")

	verify = raw_input(color.RED + "Are the above entered details correct?" + color.END + "\n\r" + ">> ")
	if verify == "no":
		print("Please restart the program")
		exit()

	elif verify == "yes":
		print("\n\r" + "Looking up prices...")

	else:
		print("Please restart the program")
		exit()

else:
	print("Wrong input. Exiting...")
	time.sleep(1)
	exit()

queryUrl = 'https://api2.fraktjakt.se/fraktjakt/query_xml?xml='
orderUrl = 'https://api2.fraktjakt.se/orders/order_xml?xml='
headers = {'Content-Type': 'application/xml'}
a = """<?xml version="1.0" encoding="UTF-8"?>
	<shipment xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	  <value>199.50</value>
	  <shipper_info>1</shipper_info>
	  <consignor>
	    <id>14613</id>
	    <key>28b26b28d42336447be4038f8a11e0cd5ea42ffd</key>
	    <currency>SEK</currency>
	    <language>en</language>
	    <encoding>UTF-8</encoding>
	    <api_version>2.9.3</api_version>
	  </consignor>
	  <parcels>
	    <parcel>
	      <weight>""" + vikt + """</weight>
	      <length>""" + langd + """</length>
	      <width>""" + bredd + """</width>
	      <height>""" + hojd + """</height>
	    </parcel>
	  </parcels>
	  <address_to>
	    <street_address_1>Hedenstorp 10</street_address_1>
	    <street_address_2></street_address_2>
	    <postal_code>33292</postal_code>
	    <residential>1</residential>
	    <country_code>SE</country_code>
	    <language>sv</language>
	  </address_to>
	</shipment>"""



req = requests.post(queryUrl + a) #HTTP POST (XML Above) variable a
resp = req.content #String Response
tree = ET.fromstring(resp) #Create XML etree 

#Place holder to pretty print XML
#rough_string = ET.tostring(tree, 'utf-8')
#reparsed = minidom.parseString(rough_string)
#print(reparsed.toprettyxml(indent="\t"))

#Iterate the XML tree and create lists
results = [] # For data print
for child in tree.iter('shipping_product'):
	results.append([child.find("name").text, child.find("arrival_time").text, child.find("price").text])

shipment_id = [] # For data print
for child in tree.iter('shipment'):
	shipment_id.append([child.find("id").text])

hidden_results = [] #For data usage
for child in tree.iter('shipping_product'):
	hidden_results.append([child.find("id").text])

warning_error = [] #Warnings/Error messages
for child in tree.iter('shipment'):
	warning_error.append([child.find("warning_message").text, child.find("error_message").text])

#Print function for Alternatives
def alternatives():
  	for r in results[1:]:
			print('\n'.join(r) + " SEK" + "\n\r")

def warnings():
	for w in warning_error:
		if w >= "":
			print("Error:" + '\n'.join(w))


warnings() #Will print if any warnings or errors occur with the provider

# Print out the cost
print(' ')
print(color.GREEN + "Best Price [ID 0]:" + color.END)
print(color.BOLD + '\n'.join(results[0]) + " SEK" + color.END)
print(' ')
print(color.GREEN + "Alternatives:" + color.END)
alternatives()

#Selection
selection = raw_input(color.RED + "Which one do you want to go with? (Best price = 0, second best = 1 etc)" + color.END + "\n\r" + ">> ")

ship_id = '\n'.join(shipment_id[0])
product_id = '\n'.join(hidden_results[int(selection)])

b = """<?xml version="1.0" encoding="UTF-8"?>
	<OrderSpecification>
	  <consignor>
	    <id>14613</id>
	    <key>28b26b28d42336447be4038f8a11e0cd5ea42ffd</key>
	    <currency>SEK</currency>
	    <language>sv</language>
	    <encoding>utf-8</encoding>
	    <api_version>2.9.3</api_version>
	  </consignor>
	  <shipment_id>""" + ship_id + """</shipment_id>
	  <shipping_product_id>""" + product_id + """</shipping_product_id>
	  <reference>My brothers shoes</reference>
	  <commodities>
	    <commodity>
	     <name>skor</name>
	     <quantity>2</quantity>
	    </commodity>
	  </commodities>
	  <recipient>
	    <name_to>Olle Klint</name_to>
	    <company_to>Hanson</company_to>
	    <telephone_to>036190220</telephone_to>
	    <email_to>test@hotmail.com</email_to>
	  </recipient>
	  <booking>
	    <pickup_date>2014-12-10</pickup_date>
	    <driving_instruction>Upp for backen och sedan over an.</driving_instruction>
	    <user_notes>Dorrkod 1112</user_notes>
	  </booking>
	</OrderSpecification>"""

req2 = requests.post(orderUrl + b) #HTTP POST (XML Above) variable b
resp2 = req2.content #String Response
tree2 = ET.fromstring(resp2) #Create XML etree 

rep = [] #List the Access code and Order ID
for child in tree2.iter('result'):
	rep.append([child.find("access_code").text])
	rep.append([child.find("order_id").text])

access_code = '\n'.join(rep[0])
order_id = '\n'.join(rep[1])

confirm = raw_input('\n' + color.BOLD + "You have selected:" + color.END + '\n' + '\n'.join(results[int(selection)]) + '\n' + '\n' + color.BOLD + "With below shipment details:" + color.END + '\n' + "PLACEHOLDER" + '\n' + '\n' + color.RED +  "Would you like to place the order? (yes/no)" + color.END + '\n' + ">>")
if confirm == "yes":
	print('\n' + "Your order has been placed with the following Order ID: " + order_id)
	print("Navigate to https://api2.fraktjakt.se/carts?locale=sv in your browser to accept the payment and print labels" + '\n')
else:
	exit()


#rough_string = ET.tostring(tree2, 'utf-8')
#reparsed = minidom.parseString(rough_string)
#print(reparsed.toprettyxml(indent="\t"))