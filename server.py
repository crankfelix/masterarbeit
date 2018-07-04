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
from multiprocessing import Process, Value


app = Flask(__name__)
CORS(app)

baseroute = "/api/v1"
cwd = os.getcwd()

top = list()
currentConnections = list()

queue = [{"status":"", "data":{"modelId":""}, "id":""}]

@app.route("/")
def index():
	return "Hallo"

@app.route(baseroute+"/queues",methods=["GET"])
def return_data():
	global queue, currentConnections
		
	if not any(dic.get('ip',None) == request.remote_addr for dic in currentConnections):
		model = createModel()
		currentConnections.append(dict(ip=request.remote_addr,connTime=time.time(),modelId=model))
	else:
		for connection in currentConnections:
			if connection['ip'] == request.remote_addr:
				connection['connTime']=time.time()
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
	with open("models/%s.json" % modelId,"r") as model:
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

	for files in os.listdir("pictures/%s" % modelId):
		filename = os.fsdecode(files)
		for pictures in os.listdir("pictures/%s/%s" % (modelId,filename)):
			pictureId = os.fsdecode(pictures)
			returnJson.append(dict(id=pictureId,label=filename))
			#returnJson.append(dict(label=filename))

	return jsonify(returnJson)

@app.route(baseroute+"/queues/<queue_id>",methods=["PUT"])
def update_queue(queue_id):
	global queue

	#if request.headers['Content-Type'] == 'application/json':
	for index, entry in enumerate(queue):
		if entry['id'] == queue_id:
			#print(request.json,file=sys.stderr)
			queue[index] = request.json
			if request.json['status']=='DONE':
				queue[index]['status']='COPYING'
			#print(queue,file=sys.stderr)
	# else:
	# 	for index, entry in enumerate(queue):
	# 		if entry['id'] == queue_id:
	# 			queue[index]['status'] = "COPYING"
	return "No Content",204

@app.route(baseroute+"/models/<model_id>",methods=["PUT"])
def update_model(model_id):
	with open("models/%s.json" % model_id,"r+") as file:
		model = json.load(file)
		labels = model['labels']
		
		model["data"]=request.json["data"]
		model['labels']=labels
		file.seek(0)
		file.write(json.dumps(model))
		file.truncate()

	# for item in queue:
	# 	if item['data']['modelId']==model_id:
	# 		item['status']=="COPYING"
	#evaluateModel(model_id)
	#createModel()


	return "No Content", 204

@app.route(baseroute+"/models/<model_id>/files/<label>/<img_id>",methods=["GET"])
def get_image(model_id,label,img_id):
	with open("pictures/%s/%s/%s" % (model_id, label, img_id), "rb") as picture:
		#retValue = (base64.b64encode(picture.read())).decode('utf-8')
		retValue = bytearray(picture.read())

	#shutil.rmtree("testPictures/%s" % model_id, ignore_errors=True)

	try:
		os.makedirs("testPictures/%s" % model_id)
	except OSError:
		pass
	try:
		os.makedirs("testPictures/%s/%s" % (model_id, label))
	except OSError:
		pass
	try:
		shutil.move("pictures/%s/%s/%s" % (model_id, label, img_id), "testPictures/%s/%s" % (model_id, label))
	except OSError:
		os.remove("pictures/%s/%s/%s" % (model_id, label, img_id))
		pass

	# try:
	# 	os.rmdir("pictures/"+label)
	# 	is_empty = True
	# except OSError:
	# 	is_empty = False
	# if is_empty:
	# 	pass

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
	global currentConnections

	mode = request.args.get('mode', default='single', type=str)
	runs = request.args.get('runs', default=-1, type=int)
	pictures = request.args.get('pictures',default=1, type=int)
	labeling = request.args.get('labeling', default='all', type=str)
	repetition = request.args.get('repetition', default='1', type=int)
	batchSize = 500 #current default value

	
	
	if mode == 'single':
		for folder in files:
			shutil.copytree("modelPictures/"+folder, "pictures/"+folder)
		#createModel()
	elif mode == 'stop':
		for t in threading.enumerate():
			print(t.getName(),file=sys.stderr)
			if t.getName() != "MainThread" and t.getName()!="checkModels":
				
				t.do_run = False
				for connections in currentConnections:
					evaluateModel(connections["modelId"],True,batchSize*pictures)
				currentConnections=list()
				#t.join()
	elif mode == 'repeat':
		t = threading.Thread(target=copyFiles, args=(runs,pictures,labeling,batchSize,repetition,))
		t.start()

	return "204"



def copyFiles(runs,pictures,labeling,batchSize,repetition):
	reps=1
	runOverview = list()
	t = threading.currentThread()
	while getattr(t, "do_run", True):
		#print(queue, file=sys.stderr)
		for item in queue:
			if item['status']=="COPYING":
				modelId=item['data']['modelId']
				if not any(dic.get('modelId',None) == modelId for dic in runOverview):
					runOverview.append(dict(modelId=modelId,runs=0))
				#if os.listdir("pictures/%s" % modelId) == []:
				if not any(os.listdir("pictures/%s/%s" % (modelId,os.fsdecode(label))) != [] for label in os.listdir("pictures/%s" % modelId)):
					labels=list()
					files = os.listdir("modelPictures")
					if labeling == 'all':
						for folder in files:
							labels.append(os.fsdecode(folder))
							try:
								os.makedirs("pictures/%s/%s" % (modelId,os.fsdecode(folder)))
							except OSError:
								pass
							count=0
							while count < int(pictures*batchSize/len(files)):
							#for count in range(0,int(pictures*batchSize/len(files))):
								picture = os.fsdecode(random.choice(os.listdir("modelPictures/%s" % os.fsdecode(folder))))
								try:
									if not os.path.exists("pictures/%s/%s/%s" % (modelId, folder, picture)):
										shutil.copy2("modelPictures/%s/%s" % (folder, picture), "pictures/%s/%s/%s" % (modelId, folder, picture))
										count+=1
								except OSError:
									pass
							# try:
							# 	shutil.copytree("modelPicturesX"+str(pictures)+"/"+folder, "pictures/"+folder)
							# except OSError:
							# 	pass
					#TODO
					else:
						while len(os.listdir("pictures/%s" % modelId))!=3:
							folder = os.fsdecode(random.choice(files))
							try:
								os.makedirs("pictures/%s/%s" % (modelId,folder))
							except OSError:
								pass
						for folder in os.listdir("pictures/%s" % modelId):
							labels.append(os.fsdecode(folder))

							count=0
							while count < int(pictures*batchSize/len(os.listdir("pictures/%s" % modelId))):
								picture = os.fsdecode(random.choice(os.listdir("modelPictures/%s" % os.fsdecode(folder))))
								try:
									if not os.path.exists("pictures/%s/%s/%s" % (modelId, folder, picture)):
										shutil.copy2("modelPictures/%s/%s" % (folder, picture), "pictures/%s/%s/%s" % (modelId, folder, picture))
										count+=1
								except OSError:
									pass			
				#createModel()
					
					with open("models/%s.json" % modelId,"r+") as modelFile:
						model = json.load(modelFile)
						model['labels']=labels
						modelFile.seek(0)
						modelFile.write(json.dumps(model))
						modelFile.truncate()
					item['status']="QUEUED"
					print(runOverview,file=sys.stderr)
					for model in runOverview:
						if model['modelId']==modelId:
							model['runs']=model['runs']+1
							if model['runs']>runs and runs!=-1 or model['runs']>40:
								item['status']="DONE"
								evaluateModel(modelId,True,batchSize*pictures)
								if reps<repetition:
									reps+=1
									createModel()
		time.sleep(1)


def createModel():
	global queue
	labels=list()
	#for files in os.listdir(cwd+"\\pictures"):
	#	filename = os.fsdecode(files)
	#	labels.append(filename)

	modelId = str(uuid.uuid4())
	queueId = str(uuid.uuid4())
	with open("models/%s.json" % modelId,"w+") as file:
		
		#model = dict(name="cifar",size=32,labels=labels,data="")
		model = dict(name="cifar",size=32,labels="",data="")

		file.write(json.dumps(model))

	#queue.append(dict(data=dict(modelId=modelId),status="QUEUED",id=queueId))
	queue.append(dict(data=dict(modelId=modelId),status="COPYING",id=queueId))
	try:
		os.makedirs("pictures/%s" % modelId)

	except OSError:
		pass

	return modelId


def evaluateModel(modelId,kill,batchSize):
	global top
	score =-1
	for count in range(0,10):

		try:
			files = os.listdir("testPictures/%s" % modelId)
		except OSError:
			return
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
			print(responseString,file=sys.stderr)
			jsonResponse = json.loads(responseString)
			for value in jsonResponse:
				if value['name'] == folder:
					score += value['score']
					print(value['score'],file=sys.stderr)
		else:
			sys.stderr.write(str(response.stderr))

	score = score/10

	evaluation=dict(modelId=modelId,score=score,batchSize=batchSize)
	with open('evaluationDump.json','a') as evaluationDumpFile:
			json.dump(evaluation,evaluationDumpFile)

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
		with open('top.json','a') as topFile:
			json.dump(top,topFile)
			#else:	
			#	os.remove("models/"+modelId+".json")
		try:
			os.remove("models/evaluated/%s.json" % modelId)
		except OSError:
			pass
		shutil.copy2("models/%s.json" % modelId, "models/evaluated/%s.json" % modelId)
		# with open('models/evaluated/scores.json','r+') as scores:
		# 	if len(scores.readlines())==0:
		# 		jsonScores=list(dict(modelId=modelId, score=score))
		# 	else:
		# 		jsonScores = json.load(scores)
		# 		for model in jsonScores:
		# 			if model['modelId']==modelId:
		# 				model[score]=score
		# 		if not any(score['modelId'] == modelId for score in jsonScores):
		# 			jsonScores.append(dict(modelId=modelId, scores=scores))
		# 	json.dump(jsonResponse,scores)		


	if kill:
		#os.remove("models/"+modelId+".json")
		shutil.rmtree("pictures/%s" % modelId,ignore_errors=True)
		shutil.rmtree("testPictures/%s" % modelId,ignore_errors=True)

@app.before_first_request
def activateJob():

	def checkModels():
		while True:
			# with open("top.json","w") as testfile:
			# 	testfile.write(str(queue))
			print(currentConnections, file=sys.stderr)
			for entry in currentConnections:
				if entry['connTime']+2400<time.time():
					evaluateModel(entry['modelId'],True,-1)
					currentConnections.remove(entry)
						#pictures+testPictures löschen
				else:
					evaluateModel(entry['modelId'],False,-1)
			time.sleep(600)

	thread = threading.Thread(target=checkModels,name="checkModels")
	thread.start()	



if __name__ == "__main__":
	#p = Process(target=checkModels, args=())
	#p.start()
	app.run(debug=True,threaded=True)
	#p.join()
	#app.run(host='0.0.0.0',threaded=True,debug=True)


#updateQueue api when processed