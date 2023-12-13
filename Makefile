DOCKER_USERNAME ?= tansan78
APPLICATION_NAME ?= babynamer
GIT_HASH ?= $(shell git log --format="%h" -n 1)

GCP_PROJECT ?= sanbeacon-1161
GCP_REGION ?= us-west1
GCP_ARTIFACT_REG_HOST ?= ${GCP_REGION}-docker.pkg.dev
GCP_ARTIFACT_REG_DIR ?= abctools

GKE_CLUSTER_NAME ?= abctools-cluster

all:
    $(info ==============================)


venv/bin/activate: requirements.txt
	python3	-m venv venv
	./venv/bin/pip install -r requirements.txt

# run all tests
# to run single tests: ./venv/bin/python3 -m unittest -v test.test_abc.TestABC_Py
test: venv/bin/activate
	./venv/bin/python3 -m test -j0

clean:
	rm -rf $(VENV)
	find . -type f -name '*.pyc' -delete


gcloud_auth:
	gcloud auth configure-docker ${GCP_ARTIFACT_REG_HOST}

gcloud_ip:
	gcloud compute addresses describe abctoolsip --global

build:
	docker build --platform linux/amd64 --tag ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:${GIT_HASH} .

push_latest:
	docker tag  ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:${GIT_HASH} \
		   ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:latest
	docker push ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:latest

release_dryrun:
	echo "docker pull ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:${GIT_HASH}"
	echo "docker tag  ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:${GIT_HASH} \
		   ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:latest"
	echo "docker push ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:latest"

release:
	docker pull ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:${GIT_HASH}
	docker tag  ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:${GIT_HASH} \
		   ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:latest
	docker push ${GCP_ARTIFACT_REG_HOST}/${GCP_PROJECT}/${GCP_ARTIFACT_REG_DIR}/${APPLICATION_NAME}:latest

# need gcloud and gke-gcloud-auth-plugin (gcloud components install gke-gcloud-auth-plugin)
gke_auth:
	gcloud config set project ${GCP_PROJECT}
	gcloud auth login

gke_cert:
	kubectl apply -f ./gke/managed-cert.yaml

gke_cluster:
	gcloud container clusters create-auto ${GKE_CLUSTER_NAME} --region=${GCP_REGION}
	gcloud container clusters get-credentials ${GKE_CLUSTER_NAME} --region=${GCP_REGION}

gke_deploy:
	gcloud container clusters get-credentials ${GKE_CLUSTER_NAME} --region=${GCP_REGION}
	kubectl apply -f ./gke/deployment.yml

gke_service:
	gcloud container clusters get-credentials ${GKE_CLUSTER_NAME} --region=${GCP_REGION}
	kubectl apply -f ./gke/service.yml

gke_ingress:
	gcloud container clusters get-credentials ${GKE_CLUSTER_NAME} --region=${GCP_REGION}
	kubectl apply -f ./gke/managed-cert-ingress.yaml


.PHONY: all test clean build gcloud_auth gke_config gke_deploy
