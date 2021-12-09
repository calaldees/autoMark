DOCKER_IMAGE:=automark
DOCKER_SOCKET:=//var/run/docker.sock:/var/run/docker.sock
# DOCKER_SOCKET is OS specific

DOCKER_RUN:=docker run --rm -v "${DOCKER_SOCKET}"

run:
	${DOCKER_RUN} ${DOCKER_IMAGE}
shell:
	${DOCKER_RUN} -it ${DOCKER_IMAGE} /bin/sh
build:
	docker build --tag ${DOCKER_IMAGE} .