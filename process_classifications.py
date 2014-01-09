from xml.dom.minidom import parse
import logging, pickle, pygal
from pygal.style import CleanStyle

#create list of acceptable tags - tag_group - then do if child.tagName in tag_group

#initialise upper counting dict
upper_dict = {}

#initialise list of tags we are interested in
tags = ['section', 'class', 'subclass', 'main-group', 'subgroup']

with open("save_doc.xml", "r") as f:
	dom = parse(f)
	
#Get each patent-classification element
for node in dom.getElementsByTagName('patent-classification'):
	#Initialise classification string to nothing
	class_level_val = ""
	logging.error(node)
	#for each component of the classification
	for child in node.childNodes:
		logging.error(child)
		#Filter out "text nodes" with newlines
		if child.nodeType is not 3 and len(child.childNodes) > 0:
			
			#Check for required tagNames - only works if element has a tagName
			if child.tagName in tags:
			
				#if no dict for selected component
				if child.tagName not in upper_dict:
					#make one
					upper_dict[child.tagName] = {}
				logging.error(child.childNodes)	
				
				#Get current component value as catenation of previous values
				class_level_val = class_level_val + child.childNodes[0].nodeValue
					
				#If value is in cuurent component dict
				if class_level_val in upper_dict[child.tagName]:
					#Increment
					upper_dict[child.tagName][class_level_val] += 1
				else:
					#Create a new entry
					upper_dict[child.tagName][class_level_val] = 1
				
print upper_dict
#Need to save results 
with open("results.pkl", "wb") as f:
	pickle.dump(upper_dict, f)

#Draw pie chart
pie_chart = pygal.Pie(style=CleanStyle)
pie_chart.title = 'Classifications for Cases (in %)'

#Get names of different sections for pie-chart labels
sections = upper_dict['section']

#Get values from second level - class
classes = upper_dict['class']
class_values = classes.keys() #list of different class values



#Iterate over keys in our section results dictionary
for k in sections.keys():
	#check if key is in class key, if so add value to set for section
	
	#Initialise list to store values for each section
	count_values = []
	for class_value in class_values:
		if k in class_value: #class key - need to iterate from class keys
			#Add to list for k
			#append_tuple = (class_value, classes[class_value]) - doesn't work
			count_values.append(classes[class_value])
			#count_values.append(append_tuple)
	pie_chart.add(k, count_values)

pie_chart.render_to_file('class_graph.svg')
