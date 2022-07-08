import queue
import random
import threading
import structlog
from reconhecimentoAudio import reconhecerAudio
from reconhecimentoSentido import gerarResposta
from speech_recognition import UnknownValueError


logger = structlog.get_logger("Lisa")


class Lisa:
    '''
    A classe Lisa contém a interpretação interna do robô da Lisa.

    A classe em si tem a variável estática lisas, que contém todas as
    instâncias de clientes da Lisa.

    Cada instância contém uma fila de pedidos, uma lista de respostas e um uid.
    '''

    lisas = {}

    def __init__(self):
        #há um máximo de Lisas por questão de uso de memória
        if len(Lisa.lisas)+1 > 256:
            logger.error("Tentou criar mais Lisas que suportado", 
                stack_info=True
            )
            raise OverflowError("Lisas demais")
        if len(Lisa.lisas) == 255:
            logger.warning("Máximo de Lisas Atingido")

        self.pedidos   = queue.Queue(32)
        self.respostas = [None]*32

        #cria um uid aleatório de 10 casas decimais
        uid = random.randint(0, int(1e11-1))
    
        #não é o melhor caminho, mas é aceitável pois 256 << 1e11-1
        while uid in Lisa.lisas.keys():
            uid = random.randint(0, int(1e11-1))
        self.uid = uid

        #coloca essa Lisa na lista de Lisas
        logger.debug("Registrando Lisa", uid=self.uid, total=len(Lisa.lisas)+1)
        Lisa.lisas[self.uid] = self
        
        #cria uma thread para processar os pedidos e começa ela
        threading.Thread(target=self.processarPedidos).start()


    def adicionarPedido(self, entrada, compreender=False):
        '''
        O método adicionarPedidos cria um pedido de processamento para a Lisa
        para uma determinada entrada, caso compreender seja falso apenas copia
        a entrada para a saída, caso seja verdadeiro interpreta a entrada por
        meio do reconhecimento de sentido da Lisa.
        O retorno é o índice que a resposta associada ao pedido terá
        '''

        #escolhendo o índice da resposta
        try:
            #cria um gerador que retorna tuples com o índice e resposta
            enumerador = enumerate(self.respostas)
            
            #cria um gerador com apenas as tuples que tem resposta igual a None
            respostas_none = filter(lambda res: res[1] == None, enumerador)
            
            #pega o primeiro Indice
            indice = next(respostas_none)[0]

        except StopIteration:
            #se não houver nenhum índice com None retorna erro
            logger.Error("Respostas demais", uid=self.uid)
            raise OverflowError("Respostas demais")
        
        if type(entrada) != str and type(entrada) != bytes:
            logger.warning("entrada de tipo inválido", 
                tipo="audio" if type(entrada) == bytes else "texto", 
                uid=self.uid
            )
            raise ValueError("Tipo inválido")

        #indica que o índice está sendo utilizado, mas não está pronto
        self.respostas[indice] = False

        logger.info("Adicionando Pedido",
            tipo="audio" if type(entrada) == bytes else "texto",
            uid=self.uid, 
            indice=indice, 
            compreender=compreender
        )

        self.pedidos.put((entrada, indice, compreender), block=False)

        return indice

    def processarPedidos(self):
        '''
        O método processarPedidos cria um loop infinito que aguarda um pedido
        de processamento e o realiza, esse método é chamado durante a 
        inicialização da instância e não deve ser chamado pelo usuário
        '''

        while True:
            try:
                pedido, indice, compreender = self.pedidos.get()
                logger.debug("Processando pedido",
                    tipo="audio" if type(pedido) == bytes else "texto",
                    uid=self.uid, 
                    indice=indice, 
                    compreender=compreender
                )

                if type(pedido) == str:
                    texto = pedido
                elif type(pedido) == bytes:
                    try:
                        texto = reconhecerAudio(pedido)
                    except UnknownValueError:
                        logger.warning("Nada foi reconhecido no áudio", 
                            uid=self.uid, 
                            indice=indice
                        )
                        texto = ""
                else:
                    logger.error("Tipo de pedido inválido", 
                        uid=self.uid, 
                        indice=indice,
                        tipo="audio" if type(pedido) == bytes else "texto"
                    )
                    texto = ""
            
                if not compreender:
                    self.respostas[indice] = texto
                    continue
            
                self.respostas[indice] = gerarResposta(texto)
            except Exception as e:
                logger.critical("Erro em processarPedidos", 
                    uid=self.uid, 
                    indice=indice,
                    exc_info=True
                )
