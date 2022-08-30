import requests
import playsound
import os
import sys
from gravarAudio import gravarAudioArquivo
from urllib.parse import urljoin
import time
import scipy.io.wavfile
import numpy as np


class ClienteLisa:
    '''
    A classe ClienteLisa é uma classe simples que define uma implementação
    pouco complexa de um cliente de comunicação, com métodos responderTexto e
    responderAudio para gerar a resposta da Lisa para um texto ou áudio,
    pegarResposta e deletarResposta para ver e deletar essas respostas e
    alguns métodos utilitátios
    '''

    def __init__(self, url_base: str, debug: bool=True):
        self.debug = debug
        self.url = url_base

        if self.debug:
            self.informacao_transferida = 0
            print("Criando Lisa...")

        #registra a Lisa e guarda o UID
        resposta = self.enviarHTTP(urljoin(self.url, "registrar"))

        self.uid = resposta.content.decode("utf-8")
        if self.debug:
            print(f"Lisa criada, uid {self.uid}")

    def __del__(self):
        if self.debug:
            print(f"\n\ninformação transferida:", end=" ")
            print(f"{self.informacao_transferida/1024**2} Mb")
    
    def responderTexto(self, texto, compreender: bool=True):
        '''
        O método responderTexto envia um pedido em texto para o servidor da
        Lisa, compreendendo ou apenas copiando a resposta
        '''

        if self.debug:
            print("enviando responder texto")
        
        url_pedido = urljoin(self.url, self.uid) + "/"
        url_pedido = urljoin(url_pedido, "responder")

        resposta = self.enviarHTTP(url_pedido, texto, headers={
            "content-type": "text/plain", 
            "compreender": "true" if compreender else "false"
        })

        return resposta.content.decode("utf-8")

    def responderAudio(self, nome_arquivo=None, compreender=True):
        '''
        O método responderAudio faz o mesmo que responderTexto mas para um 
        áudio, além de gravar um arquivo de áudio temporário do usuário caso
        não haja nenhum input de áudio prévio
        '''

        if self.debug:
            print(f"enviando responder texto")

        gravar_arquivo = nome_arquivo is None
        if gravar_arquivo:
            nome_arquivo = "tmp.wav"
            self.gravar(nome_arquivo)
        
        arq = open(nome_arquivo, "rb")
            

        url_pedido = urljoin(self.url, self.uid) + "/"
        url_pedido = urljoin(url_pedido, "responder")

        resposta = self.enviarHTTP(url_pedido, arq, headers={
            "content-type": "audio/wav", 
            "compreender": "true" if compreender else "false"
        })

        arq.close()
        
        if gravar_arquivo:
            os.remove(nome_arquivo)

        return resposta.content.decode("utf-8")
    
    def pegarResposta(self, indice, audio=False):
        '''
        O método pegarResposta pede a resposta de determinado índice em áudio
        ou texto, retornando em ambos os casos um objeto bytes
        '''

        url_pedido = urljoin(self.url, self.uid) + "/"
        url_pedido = urljoin(url_pedido, "respostas") + "/"
        url_pedido = urljoin(url_pedido, indice)
        resposta = self.enviarHTTP(url_pedido, headers={
            "accept": "audio/wav" if audio else "text/plain"
        }, method="get")
        
        return resposta.content
    
    def deletarResposta(self, indice):
        '''
        O método deletarResposta deleta a resposta de determinado índice
        '''

        url_pedido = urljoin(self.url, self.uid) + "/"
        url_pedido = urljoin(url_pedido, "respostas") + "/"
        url_pedido = urljoin(url_pedido, indice)
        resposta = self.enviarHTTP(url_pedido, method="delete")


    def falar(self, audio):
        '''
        O método falar fala um áudio contido em um objeto bytes
        '''
        
        if self.debug:
            print(f"falando áudio de tamanho {len(audio)//1024} kb")
        
        dados = np.frombuffer(audio, dtype=np.float64)

        nome_arquivo = "tmp.wav"
        scipy.io.wavfile.write(nome_arquivo, 24000, dados)
        playsound.playsound(nome_arquivo)
        os.remove(nome_arquivo)
    
    def gravar(self, arq):
        '''
        O método gravar grava áudio do usuário em um arquivo arq
        '''

        if self.debug:
            print(f"gravando áudio em {arq}...")
        gravarAudioArquivo(arq)

    def enviarHTTP(self, url, content=None, headers=None, method="post"):
        '''
        O método enviarHTTP envia um pedido de HTTP de forma uniforme com
        informações de debug úteis
        '''

        t_ini = time.time()
        try:
            if method == "post":
                resposta = requests.post(url, content, headers=headers)
            elif method == "delete":
                resposta = requests.delete(url)
            elif method == "get":
                resposta = requests.get(url, content, headers=headers)
        except requests.exceptions.ConnectionError:
            print(f"Erro! Não foi possível conectar a {url}")
            sys.exit(1)
        t_fim = time.time()

        if self.debug:
            self.informacao_transferida += len(resposta.content)

            print(f"retorno demorou {t_fim-t_ini}", end=" ")
            print(f"com código {resposta.status_code}", end=" ")
            try:
                print(f"com mimetype {resposta.headers['content-type']}")
            except KeyError:
                print("sem mimetype")
            
            if resposta.status_code >= 400:
                print("-------------")
                print("dump de erro:")
                print("-------------")
                print(resposta.headers)
                print("-------------")
                print(resposta.content.decode("utf-8"))
                print("-------------")

        if resposta.status_code >= 400:
            raise IOError("Retorno incorreto")
        return resposta
            
ajuda = '''
Inputs possíveis:

enviarAudio: grava e envia um áudio para a Lisa falar
enviarTexto: envia um texto para a Lisa falar (escrever pela linha de input)
responderAudio: grava e envia um áudio para a Lisa responder
responderTexto: envia um texto para a Lisa responder \
(escrever pela linha de input)

Todos esses inputs retornam um número com o índice da resposta que a Lisa gerou
Para ver a resposta utilize:

pegarAudio: pede o áudio de TTS da Lisa de um index e fala
pegarTexto: pede o texto de um index

deletarResposta: deleta a resposta em um index
'''

if __name__ == "__main__":
    try:
        lisa = ClienteLisa("http://localhost:8080", True)
    except IOError:
        print("Erro na criação da cliente")
        sys.exit(-1)

    print("Programa de cliente teste da Lisa")
    print("Utilize \"ajuda\" para ver os comandos possíveis")
    try:
        while True:
            lido = input("input: ")
            try:
                comando = lido.split()[0]
            except IndexError:
                break
                
            try:
                if comando == "enviarAudio":
                    indice = lisa.responderAudio(None, compreender=False)
                    print(indice)
                elif comando == "enviarTexto":
                    texto = lido[lido.find(comando)+len(comando)+1:]
                    indice = lisa.responderTexto(texto, compreender=False)
                    print(indice)
                elif comando == "responderAudio":
                    indice = lisa.responderAudio(None)
                    print(indice)
                elif comando == "responderTexto":
                    texto = lido[lido.find(comando)+len(comando)+1:]
                    indice = lisa.responderTexto(texto)
                    print(indice)
                elif comando == "pegarTexto":
                    indice = lido.split()[1]
                    texto = lisa.pegarResposta(indice, audio=False)
                    print(texto.decode("utf-8"))
                elif comando == "pegarAudio":
                    indice = lido.split()[1]
                    audio = lisa.pegarResposta(indice, audio=True)
                    lisa.falar(audio)
                elif comando == "deletarResposta":
                    indice = lido.split()[1]
                    lisa.deletarResposta(indice)
                    print("ok")
                elif comando == "ajuda":
                    print(ajuda)
                else:
                    print("Erro, input invalido")
            except IOError:
                continue
            except IndexError:
                print("pegarAudio, pegarTexto e deletarResposta", end=" ")
                print("precisam de um índice")
                continue
        
    except (EOFError, KeyboardInterrupt):
        pass