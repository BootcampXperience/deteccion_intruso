import imutils
from imutils import paths
import os
import pickle
import configparser
from datetime import datetime
import time
import cv2
import face_recognition
from pyicloud import PyiCloudService
from alright import WhatsApp
import vlc
import pyautogui
from pynput.keyboard import Key, Controller
keyboard = Controller()
 
#Busca todos los folder dentro del folder Imagenes
folders = list(paths.list_images('Imagenes'))
knownEncodings = []
knownNames = []
#Recorre imagenes en cada folder
for (i, imagePath) in enumerate(folders):
    #Extraye el nombre del folder
    nombre = imagePath.split(os.path.sep)[-2]
    imagen = cv2.imread(imagePath)
    rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    #Usamos Face_recognition para localizar el rostro
    cajas = face_recognition.face_locations(rgb, model='hog')
    encodings = face_recognition.face_encodings(rgb, cajas)
    #Después de convertir cada imagen a encoding lo guardamos en listas
    for encoding in encodings:
        knownEncodings.append(encoding)
        knownNames.append(nombre)
#Convertimos las listas en diccionario
data = {"encodings": knownEncodings, "names": knownNames}
#Guardamos el diccionario en un archivo para posteriormente comparar las imagenes recibidas de la cámara
f = open("rostros_enc", "wb")
f.write(pickle.dumps(data))
f.close()

#Configurando Geolocalizacion
config = configparser.ConfigParser()
config.read('login.ini')
usuario = config.get('login', 'usuario')
contraseña = config.get('login', 'contraseña')
api = PyiCloudService(usuario, contraseña)
latitud = api.iphone.location()['latitude']
longitud = api.iphone.location()['longitude']

#Configurando WhatsApp
messenger = WhatsApp()

#Cargamos el Modelo haarcascade para detección de rostro frontal
faceCascade = cv2.CascadeClassifier('/Users/alejandro/miniforge3/pkgs/libopencv-4.5.5-py39h86e1ac9_9/share/opencv4/haarcascades/haarcascade_frontalface_alt2.xml')
#Cargamos nuestra base de rostros conocidos
data = pickle.loads(open('rostros_enc', "rb").read())
#Cargamos el audio
p = vlc.MediaPlayer("sirena.mp3")
contador = 0

def avisar_policia():
    p.play()
    latitud = api.iphone.location()['latitude']
    longitud = api.iphone.location()['longitude']
    localizacion='https://www.google.com/maps/place/' + str(latitud) + str(longitud)
    titulo = 'INTRUSO DETECTADO!!!'
    placa = 'Placa Vehículo: IMGROOT'
    horario = 'Horario: ' + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cv2.imwrite('intruso.png', frame)
    mensajes = [titulo, horario, placa, localizacion]

    messenger.search_chat_by_name('Policia')
    for mensaje in mensajes:
        messenger.send_message(mensaje)
    messenger.send_picture('intruso.png','Intruso')
    pyautogui.hotkey('command', 'tab', interval=0.1)
    time.sleep(0.1)
    pyautogui.click()
    time.sleep(0.1)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    pyautogui.hotkey('command', 'tab', interval=0.1)

print("Video Iniciado")
video_capture = cv2.VideoCapture(0)
ultima_ejecucion = time.time()

#Iniciamos la transmisión
while True:
    ret, frame = video_capture.read()
    height,width = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rostros = faceCascade.detectMultiScale(gray,
             scaleFactor=1.1,
             minNeighbors=5,
             minSize=(60, 60),
             flags=cv2.CASCADE_SCALE_IMAGE)
    
    #Mostrando Contador
    cv2.rectangle(frame, (0, 0), (width, int(height*0.1)), (0,0,0), -1)
    cv2.putText(frame,'Contador: '+str(contador),(int(width*0.65), int(height*0.08)), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)
 
    #Recibimos la imagen de la cámara y la transformamos a encoding
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb)
    nombres = []
    
    #Recorremos para cada rostro detectado en cámara
    for encoding in encodings:
       #Comparamos con la base de rostros conocidos
        matches = face_recognition.compare_faces(data["encodings"], encoding)
        nombre = "Desconocido"
        #Si encontramos un rostro conocido
        if True in matches:
            #Guardamos la posición donde encontramos el rostro en nuestra base de rostros conocidos
            matchedIdxs = [i for (i, b) in enumerate(matches) if b]
            counts = {}
            #Recorremos todos los rostros que coinciden de nuestra base
            for i in matchedIdxs:
                nombre = data["names"][i]
                counts[nombre] = counts.get(nombre, 0) + 1
            #Actualizamos el nombre con el rostro que tuvo más coincidencias
            nombre = max(counts, key=counts.get)
 
        #Adicionamos nombre a la lista
        nombres.append(nombre)

        #Recorriendo los rostros detectados
        for ((x, y, w, h), nombre) in zip(rostros, nombres):
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            #Algoritmo de deteccion de intruso
            if (nombre=='Desconocido'):
                cv2.putText(frame,'Desconocido',(10, int(height*0.08)), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)
                if contador<10: contador+=1

            if (nombre=='Alejandro'):
                cv2.putText(frame,'Alejandro',(10, int(height*0.08)), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)
                contador-=1
                
            if contador==10 and (time.time() - ultima_ejecucion)>=30:
                ultima_ejecucion = time.time()
                avisar_policia()
            elif (contador>0 and contador<10):
                p.stop()
            elif contador<0:
                contador=0
                
    cv2.imshow("Frame", frame)
    
    #Tecla de salida - acaba la transmisión
    if cv2.waitKey(1) & 0xFF == ord('q'):
        video_capture.release()
        cv2.destroyAllWindows()
        break