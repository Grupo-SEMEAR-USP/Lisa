import flask

from TTSLisa import gerarStreamAudio
from reconhecimentoSentido import gerarResposta
from reconhecimentoAudio import reconhecerAudio
from speech_recognition import UnknownValueError
from Lisa import Lisa
import queue


servidor = flask.Flask("servidorLisa")


@servidor.route("/registrar", methods=["POST"])
def registrar():
    '''
    A função registrar registra uma nova instância de Lisa, 
    retornando um valor do ID do cliente.
    '''

    try:
        lisa = Lisa()
    except OverflowError:
        flask.Response("Lisas demais", status=507)
    
    return flask.Response(str(lisa.uid), status=201)


@servidor.route("/<uid>/responder", methods=["POST"])
def responder(uid):
    '''
    A função responder cria uma entrada nas respostas com o texto da resposta
    da Lisa a um áudio ou texto recebido no corpo do pedido. Essa é a função 
    principal do servidor e é essencial para o funcionamento da robô.
    
    Caso o header "compreender" esteja presente e tenha valor "false", o texto
    não passará pelo processamento de sentido, sendo apenas copiado para a
    lista de respostas
    '''
    
    #identificando o cliente
    try:
        lisa = Lisa.lisas[int(uid)]
    except KeyError:
        return flask.Response("Lisa não encontrada", status=404)
    except ValueError:
        return flask.Response("Uid não é um número", status=400)



    #identificando o tipo de entrada
    if flask.request.content_type == "text/plain":
        #pega o texto todo como uma string
        try:
            entrada = flask.request.get_data().decode("utf-8")
        except UnicodeDecodeError:
            return flask.Response("Entrada não é UTF-8", status=400)

    elif flask.request.content_type == "audio/wav":
        #pega o áudio todo como uma sequência de bytes
        entrada = flask.request.get_data()
    
    else:
        #se não recebems texto ou wav algo está errado
        return flask.Response("Tipo de dado não suportado", status=415)


    #identificando o header de compreensão
    try:
        compreender = not flask.request.headers["compreender"] == "false"
    except KeyError:
        compreender = True

    #processando a entrada
    try:
        #identifica o tipo e transforma para texto caso seja um áudio
        indice_pedido = lisa.adicionarResposta(entrada, compreender)
    except queue.Full:
        return flask.Response("Muitos pedidos no buffer", status=507)
    except OverflowError:
        return flask.Response("Respostas demais", status=507)

    #retornando que deu tudo certo
    return flask.Response(str(indice_pedido))


@servidor.route("/<uid>/respostas/<indice>", methods=["GET", "DELETE"])
def resposta(uid, indice):
    '''
    resposta retorna a resposta em áudio ou texto com um índice específico,
    ou deleta a resposta caso o metodo seja esse
    '''

    try:
        lisa = Lisa.lisas[int(uid)]
    except KeyError:
        return flask.Response("Lisa não encontrada", status=404)
    except ValueError:
        return flask.Response("Uid não é um número", status=400)

    try:
        resposta = lisa.respostas[int(indice)]
    except ValueError:
        return flask.Response("Indice não é um número", status=400)
    except KeyError:
        return flask.Response("Indice não está entre 0 e 32", status=400)


    if flask.request.method == "DELETE":
        lisa.respostas[int(indice)] = None
        return flask.Response(status=200)


    if type(resposta) == bool and resposta == False:
        return flask.Response("Resposta não está pronta", status=202)
    if type(resposta) == type(None):
        return flask.Response("Resposta não encontrada", status=404)
    
    try:
        tipo_pedido = flask.request.headers["accept"]
    except KeyError:
        return flask.Response("Sem header Accept", status=400)

    if tipo_pedido == "text/plain":
        return flask.Response(resposta)

    if tipo_pedido == "audio/mp3":
        try:
            gerador = gerarStreamAudio(resposta)
        except AssertionError:
            return flask.Response("Erro no TTS", status=500)
        return servidor.response_class(gerador())
    
    #se não recebems texto ou wav algo está errado
    return flask.Response(status=415)


if __name__ == '__main__':
    #roda o servidor, em modo de debug, escutando na porta 8080 em todos os
    #hostnames, ou seja, é possível acessar o servidor em 
    #http://localhost:8080 ou http://192.168.0.seu_ip:8080, por exemplo

    servidor.run("0.0.0.0", 8080, True)
