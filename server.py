from flask import Flask, json, request, abort, make_response
import base64
import uuid
import os

app = Flask(__name__)

@app.route("/")
def index():
	return "Hallo"

@app.route("/api/v1/data",methods=["GET"])
def return_data():
	cwd = os.getcwd()
	returnJson = dict()

	for file in os.listdir(cwd+"\\pictures"):
		filename = os.fsdecode(file)

		with open(cwd+"\\pictures\\"+file, "rb") as zipFile:
			retValue = str(base64.b64encode(zipFile.read()))
		
		returnJson[filename] = retValue
		os.remove(cwd+"\\pictures\\"+file)

	return json.dumps(returnJson)



@app.route("/api/v1/model",methods=["POST"])
def accept_model():
	if not request.json:
		abort(400)
	cwd = os.getcwd()
	with open(cwd+"\\models\\"+str(uuid.uuid4())+".json","w+") as file:
		file.write(str(request.json))

	return "nice",201


if __name__ == "__main__":
	app.run(debug=True)

#start local testing with pictures
#get results back to check which model is the best by using random pictures 
#delete bad models