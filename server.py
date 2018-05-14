from flask import Flask, json, request, abort, make_response, jsonify
from flask_cors import CORS
import base64
import uuid
import os
import sys
from shutil import copy2
import random
from PIL import Image
from Naked.toolshed.shell import muterun_js
import io
import time
import shutil
import threading
from collections import Counter

app = Flask(__name__)
CORS(app)

baseroute = "/api/v1"
cwd = os.getcwd()

top = list()

queue = [{"status":"", "data":{"modelId":""}, "id":""}]

@app.route("/")
def index():
	return "Hallo"

@app.route(baseroute+"/queues",methods=["GET"])
def return_data():
	global queue
	response = list()
	for entry in queue:
		if entry['status'] == "QUEUED":
			response.append(entry)
			print(response)
			return jsonify(response)

	#status = request.args.get('status', default='none', type=str)

	# if queue[0]["status"] == "PROCESSING":
	# 	return '[]'

	# if os.listdir(cwd+"\\pictures") != []: 
	# 	queue[0]["status"] = "QUEUED"
	# 	createModel()
	# 	time.sleep(7) 
	# 	return jsonify(queue) 
	# else: 
	# 	return jsonify("")

	# if queue[0]["status"] == "DONE":
	# 	return '[]'

	return jsonify("")

#not officially used
@app.route(baseroute+"/model",methods=["POST"])
def accept_model():
	if not request.json:
		abort(400)
	with open(cwd+"\\models\\"+str(uuid.uuid4())+".json","w+") as file:
		file.write(str(request.json))

	return "nice",201

@app.route(baseroute+"/models/<modelId>",methods=["GET"])
def get_model(modelId):
	with open(cwd+"\\models\\"+modelId+".json","r") as model:
		#retValue = dict(id=model.read())
		retmodel = model.read()
		retmodel = json.loads(retmodel.replace("'",'"'))
		#print(retmodel)
		retmodel['id'] = modelId
		#print(model.read(), file=sys.stderr)
	return jsonify(retmodel)

@app.route(baseroute+"/models/<modelId>/files", methods=["GET"])
def get_images(modelId):
	#[{"id":"2344","label","XXXX"}]

	returnJson = list()

	for files in os.listdir(cwd+"\\pictures"):
		filename = os.fsdecode(files)
		for pictures in os.listdir(cwd+"\\pictures\\"+filename):
			pictureId = os.fsdecode(pictures)
			returnJson.append(dict(id=pictureId,label=filename))
			#returnJson.append(dict(label=filename))

	return jsonify(returnJson)

@app.route(baseroute+"/queues/<queue_id>",methods=["PUT"])
def update_queue(queue_id):
	global queue

	if request.headers['Content-Type'] == 'application/json':
		for index, entry in enumerate(queue):
			if entry['id'] == queue_id:
				print(response.json)
				queue[index] = request.json
	else:
		for index, entry in enumerate(queue):
			if entry['id'] == queue_id:
				queue[index]['status'] = "DONE"
	return "No Content",204

@app.route(baseroute+"/models/<model_id>",methods=["PUT"])
def update_model(model_id):
	with open(cwd+"\\models\\"+model_id+".json","r") as file:
		model = json.load(file)
		model["data"]=request.json["data"]
	with open(cwd+"\\models\\"+model_id+".json","w+") as file:
		file.write(json.dumps(model))
	evaluateModel(model_id)
	#createModel()

	return "No Content", 204

@app.route(baseroute+"/models/<model_id>/files/<label>/<img_id>",methods=["GET"])
def get_image(model_id,label,img_id):
	with open(cwd+"\\pictures\\"+label+"\\"+img_id, "rb") as picture:
		#retValue = (base64.b64encode(picture.read())).decode('utf-8')
		retValue = bytearray(picture.read())

	try:
		os.makedirs("testPictures/%s" % model_id)
	except OSError:
		pass

	try:
		os.makedirs("testPictures/%s/%s" % (model_id, label))
	except OSError:
		pass

	shutil.move("pictures/"+label+"/"+img_id, "testPictures/%s/%s" % (model_id, label))

	#os.remove(cwd+"\\pictures\\"+label+"\\"+img_id)
	
	try:
		os.rmdir("pictures/"+label)
		is_empty = True
	except OSError:
		is_empty = False
	if is_empty:
		pass

	#return jsonify(retValue)
	return retValue

@app.route(baseroute+"/test",methods=["POST"])
def predict_label():
	upload = io.BytesIO(request.get_data())

	im = Image.open(upload).convert('RGBA')
	imList = list(im.getdata())

	pv = list()
	for index,x in enumerate(imList):
		for ti in imList[index]:
			pv.append(ti/255.0-0.5)
	with open("convertedImage.txt","w") as convertedImage:
			convertedImage.write(str(pv))

	responses = list()

	for model in os.listdir("models"):
		modelId = os.fsdecode(model)
		response = muterun_js('predict.js models/%s convertedImage.txt' % modelId)
		if response.exitcode == 0:
			responseString = (response.stdout).decode("utf-8")
			jsonResponse = json.loads(responseString)
			print(jsonResponse)
			responses.append(jsonResponse)
			# if not labels:
			# 	labels = jsonResponse
			# else:
			# 	for value in jsonResponse: #durchschnitt über alle modelle oder maximum oder voting??
			# 		for index, existingValue in enumerate(labels):
			# 			if value['name'] == existingValue['name'] and int(existingValue['score']) < int(value['score']):
			# 				labels[index] = value
		else:
			sys.stderr.write(str(response.stderr))
	#list of all labels
	labels = list()
	for label in responses[0]:
		labels.append(label['name'])

	#highest label of every model
	highestLabelsWithScore = list()
	highestLabels = list()
	for response in responses:
		highestLabel = ""
		score = 0
		for label in response:
			if label['score'] > score:
				score = label['score']
				highestLabel = label['name']

		highestLabelsWithScore.append(dict(label=highestLabel,score=score))
		highestLabels.append(highestLabel)

	#vote based:
	count = dict(Counter(highestLabels))

	#confidence based
	highestLabelsCumulated = list()
	for label in highestLabelsWithScore:
		if not any(dic.get('label',None) == label['label'] for dic in highestLabelsCumulated):
			highestLabelsCumulated.append(label)
		else:
			for labelToUpdate in highestLabelsCumulated:
				if labelToUpdate['label'] == label['label']:
					labelToUpdate['score'] = labelToUpdate['score'] + label['score']
	print(highestLabelsCumulated)


	return jsonify([count,highestLabelsCumulated])

@app.route(baseroute+"/top",methods=["GET"])
def get_top():
	return jsonify(top)

@app.route(baseroute+"/push", methods=["GET"])
def push_files():

	mode = request.args.get('mode', default='single', type=str)
	runs = request.args.get('runs', default=-1, type=int)
	pictures = request.args.get('pictures',default=1, type=int)
	labeling = request.args.get('labeling', default='all', type=str)

	files = os.listdir(cwd+"/modelPicturesX"+str(pictures))
	
	if mode == 'single':
		for folder in files:
			shutil.copytree("modelPicturesX"+str(pictures)+"/"+folder, "pictures/"+folder)
		createModel()
	elif mode == 'stop':
		for t in threading.enumerate():
			if t.getName() != "MainThread":
				print(t.getName())
				t.do_run = False
				#t.join()
	elif mode == 'repeat':
		t = threading.Thread(target=copyFiles, args=(runs,pictures,labeling,))
		t.start()

	return "204"



def copyFiles(runs,pictures,labeling):
	elapsedRuns = 0
	t = threading.currentThread()
	while getattr(t, "do_run", True):
		if os.listdir("pictures") == []:
			print("copying files")
			files = os.listdir("modelPicturesX"+str(pictures))
			if labeling == 'all':
				for folder in files:
					try:
						shutil.copytree("modelPicturesX"+str(pictures)+"/"+folder, "pictures/"+folder)
					except OSError:
						pass
			else:
				while len(os.listdir("pictures"))!=3:
					folder = os.fsdecode(random.choice(files))
					if folder not in os.listdir("pictures"):
						try:
							shutil.copytree("modelPicturesX"+str(pictures)+"/"+folder, "pictures/"+folder)
						except OSError:
							pass

			createModel()
			elapsedRuns+=1

		if elapsedRuns==runs and runs!=-1:
			return
		time.sleep(5)


def createModel():
	global queue
	labels=list()
	for files in os.listdir(cwd+"\\pictures"):
		filename = os.fsdecode(files)
		labels.append(filename)

	modelId = str(uuid.uuid4())
	queueId = str(uuid.uuid4())
	with open(cwd+"\\models\\"+modelId+".json","w+") as file:
		
		model = dict(name="cifar",size=32,labels=labels,data="")

		file.write(json.dumps(model))

	queue.append(dict(data=dict(modelId=modelId),status="QUEUED",id=queueId))

	#queue[0]["data"]["modelId"]=modelId



def evaluateModel(modelId):
	global top
	score =-1
	for count in range(0,10):

		files = os.listdir("testPictures/%s" % modelId)
		folder = os.fsdecode(random.choice(files))
		pictures = os.listdir("testPictures/%s/%s" % (modelId, folder))
		pictureId = os.fsdecode(random.choice(pictures))
		im = Image.open("testPictures/%s/%s/%s" % (modelId, folder, pictureId)).convert('RGBA')
		imList = list(im.getdata())

		pv = list()
		for index,x in enumerate(imList):
			for ti in imList[index]:
				pv.append(ti/255.0-0.5)
		with open("convertedImage.txt","w") as convertedImage:
			convertedImage.write(str(pv))
		#subprocess call
		response = muterun_js('predict.js models/%s.json convertedImage.txt' % modelId)
		if response.exitcode == 0:
			responseString = (response.stdout).decode("utf-8")
			jsonResponse = json.loads(responseString)
			for value in jsonResponse:
				if value['name'] == folder:
					score += value['score']
					print(value['score'])
		else:
			sys.stderr.write(str(response.stderr))

	score = score/10

	if score>20:
		if len(top)<10:
			top.append(dict(modelId=modelId+".json",score=score))
		#calculate the top list
		else:
			lowestScore = 1000
			position = -1
			for index, item in enumerate(top):
				print(item['score'])
				if item['score'] < lowestScore:
					lowestScore = item['score']
					position = index
			if score > lowestScore:
				top[position] = dict(modelId=modelId+".json",score=score)
		with open('top.json','w') as topFile:
			json.dump(top,topFile)
			#else:	
			#	os.remove("models/"+modelId+".json")

	else:
		os.remove("models/"+modelId+".json")

	for folders in files:
		for pics in os.listdir("testPictures/%s/%s" % (modelId,folders)):
			os.remove("testPictures/%s/%s/%s" % (modelId,folders,pics))
		try:
			os.rmdir("testPictures/%s/%s" % (modelId,folders))
			is_empty = True
		except OSError:
			is_empty = False
		if is_empty:
			pass
		try:
			os.rmdir("testPictures/%s" % modelId)
			is_empty = True
		except OSError:
			is_empty = False
		if is_empty:
			pass



if __name__ == "__main__":
	#app.run(debug=True)
	app.run(host='0.0.0.0',threaded=True)

#updateQueue api when processed