from calendar import c
import sys
import os
import errno
import datetime
import logging

######### FORMA DE USO ###########
# 4 tipos de logs diferentes

## log.log("i", "mensaje") --> logger.info
## log.log("w", "mensaje") --> logger.warning
## log.log("e", "mensaje") --> logger.error
## log.log("c", "mensaje") --> logger.critical

##################################

dir_path = os.path.dirname(os.path.abspath(__file__))
tipo = ""
msj = ""

def createFolderIfnotExist(pathFolder):
    if not os.path.exists(pathFolder):
        try:
            os.makedirs(pathFolder)
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

def todayFormated(format):
    hoy = datetime.datetime.now()
    todayFormat = hoy.strftime(format)
    return todayFormat


def inicializacion():
    hoyFormat = todayFormated("%Y%m%d")
    carpetaLogs = os.path.join(dir_path, "..", "LOGS")
    createFolderIfnotExist(carpetaLogs)

    #### LOG CONFIGURATION ###
    logging.basicConfig(filename= os.path.join(carpetaLogs, '{}.log'.format(hoyFormat)), format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)


def log(tipo, msj):
    if tipo == 'i':
        logging.info(msj)
    elif tipo == 'w':
        logging.warning(msj)
    elif tipo == 'e':
        logging.error(msj)
    elif tipo == 'c':
        logging.critical(msj)


inicializacion()
log(tipo, msj)

