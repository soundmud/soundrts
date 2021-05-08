Manual do jogo
==============

.. language: pt_BR
.. contents::

1. Introdução
-------------

Bem-vindo ao SoundRTS!

SoundRTS é um jogo de estratégia em tempo real inspirado por Warcraft e Starcraft, mas um áudio-jogo, portanto adaptado para cegos.
Nesse jogo, você explorará os arredores, explorará minas de ouro e bosques,
construirá, recrutará operários e soldados, e lutará contra o inimigo!

Por padrão o jogo está no modo mapa: você está virado para norte pode
selecionar todos os objetos sem a necessidade de se virar.
Você pode, todavia, jogar no modo em primeira pessoa, útil para
exploração e ataque.

2. Tutorial
-----------

Esse tutorial irá ajudá-lo a aprender os principais controles do jogo.

2.1 Tutorial do capítulo 1
^^^^^^^^^^^^^^^^^^^^^^^^^^

Se você usa o Jaws ou alguma revisão de tela, talvez você precise
desativá-la para ter acesso completo ao teclado.

Quando o jogo começar, você ouvirá o nome do quadrado onde você está: "A1".
A presença de uma mina de ouro em A1 é também anunciada. Para examinar
esse quadrado, pressione Tab algumas vezes.
Você vai notar que esse quadrado tem apenas uma saída (um caminho), uma
mina de ouro, um bosque, prefeitura 1 (é a sua base), e o operário 1.

Então pressione "Page Down" para saber se outro quadrado pode ser
examinado. Você ouvirá "C1", que contém (pressione Tab para saber) uma
fazenda, um caminho, um bosque e o soldado 1.

Se você pressionar "Page Down" novamente, estará de novo em "A1". Isso
significa que apenas dois quadrados podem ser examinados no momento.

Uma forma alternativa de se mover pelo mapa é usar as setas. Assim você pode
passar pelos quadrados desconhecidos para selecionar um deles como alvo de uma ordem.

O objetivo desse mapa é construir uma fazenda e um quartel. Apenas o
operário pode fazer isso. Mas ele precisa de ouro e madeira, e um
espaço livre (um terreno). Para saber quanto de ouro, madeira e comida
você tem, pressione z, x e c, respectivamente.

Vamos mandar o operário recolher ouro. Primeiro, para controlá-lo, pressione Q
até que você ouça "operário 1, esperando ordens!". Então, pressione A
até selecionar "explorar"; então pressione Tab algumas vezes para selecionar a mina de ouro, e dê
Enter para confirmar. O operário vai começar a extrair o ouro.

Para ir mais rápido você precisará de mais operários. Pressione Q para
controlar a prefeitura, pressione A até Recrutar Operário e pressione Enter para confirmar.
Após alguns segundos, um novo operário, operário 2, aparecerá.

Para mandar o operário 2 recolher madeira, faça como o primeiro ou, para ir mais rápido, pressione Q até controlar o operário 2, então
pressione Tab para selecionar a mina de ouro, e finalmente pressione "Backspace".
Essa tecla faz a ação padrão no alvo selecionado: aqui, a ação padrão é
"explorar a mina de ouro".

Antes de recrutar um terceiro operário, vamos dizer para a prefeitura 1
que todos os novos operários deverão explorar a mina de ouro. Para fazer
isso, pressione Q até controlar a prefeitura 1. Então pressione Tab até selecionar a mina de
ouro. Finalmente, pressione "Backspace" para dar a ordem padrão para a
prefeitura : "reunião à mina de ouro".
Agora você pode recrutar o terceiro operário. Pressione A até recrutar
operário e pressione "Enter" para confirmar.

Quando você tiver ouro suficiente ou quando a mina se esgotar,
pressione D para controlar todos os operários, Tab até selecionar o
bosque e "Backspace" para confirmar.

O resto não é difícil.

2.2 Tutorial do capítulo 2
^^^^^^^^^^^^^^^^^^^^^^^^^^

Dica: agrupe suas unidades de combate. Para fazer isso, controle-as
(com a letra S) e faça-as patrulhar entre os quadrados que você quer
proteger.

2.3 Dicas e truques
^^^^^^^^^^^^^^^^^^^

- Mantenha suas forças focadas.
- Faça seus soldados patrulharem. Soldados que patrulham podem proteger uma zona maior enquanto mantém as forças focadas.
- Use pontos de encontro nas construções. As construções que tem a possibilidade de recrutar unidades podem definir um ponto de encontro. As novas unidades vão ter
  esse ponto de encontro como alvo. Por exemplo um novo operário explorará a mina de ouro.

- Use o modo defensivo para espiar. Uma unidade no modo defensivo vai fugir se ela encontrar inimigos mais fortes. Com isso você pode saber quantos inimigos tem
  num quadrado sem sacrificar a espia. Os operários
  ficam no modo defensivo por padrão mas os soldados podem ser configurados para ficarem nesse modo também.

- Uma unidade que fugir esquece suas ordens. Um operário que fugir não vai voltar a recolher ouro, enquanto que se ele lutasse e sobrevivesse, ele iria voltar e
  exploraria novamente a mina.


3. Lista de comandos
--------------------

O jogo consiste em dar ordens às suas unidades e construções. Para dar
uma ordem à uma unidade, você deve controlá-la primeiro.
Se você pressionar F10 durante o jogo, você irá para o menu da partida.

Movendo-se pelo mapa
^^^^^^^^^^^^^^^^^^^^

As setas fazem você se mover de um quadrado a outro pelo mapa. Se um
caminho direto existir entre o quadrado que você estiver e o novo, você
ouvirá um som dependendo do tipo do caminho (caminho ou ponte). Se não existir um
caminho direto, você ouvirá um som de colisão e permanecerá no mesmo
quadrado (pressione control + setas para passar por cima do obstáculo).
Se você não conhecer ainda se um caminho existe (quadrado desconhecido)
então nenhum som será ouvido.

Pressione shift + setas para se mover vários quadrados de uma vez.

Outra forma de se mover pelo mapa é pressionar Page Up, que levará você ao
próximo quadrado interessante sem passar por quadrados vazios. Desde o SoundRTS 1.1 alpha
3, algumas variantes estão disponíveis:

- pressione Alt + PageUp/PageDown para selecionar o quadrado desconhecido anterior / seguinte.
- pressione Shift + PageUp/PageDown para selecionar o quadrado anterior / seguinte que contenha recursos.

Quando você controlar uma unidade e pressionar a Barra de espaço, você a
seguirá quando ela mover de um quadrado a outro.

Escolhendo uma unidade para controlar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para controlar a próxima unidade local, pressione Q.

Para controlar a próxima construção, pressione W.
Para controlar o próximo operário, pressione E. Para controlar todos os operários locais, pressione D.
Para controlar o próximo operário desocupado, pressione Alt + E. Para controlar todos os operários desocupados locais, pressione Alt + D.
Para controlar o próximo soldado, pressione R. Para controlar todos os soldados locais, pressione F.
Para controlar o próximo arqueiro, pressione T. Para controlar todos os arqueiros locais, pressione G.
Para controlar o próximo cavaleiro, pressione Y. Para controlar todos os cavaleiros locais, pressione H.
Para controlar a próxima catapulta, pressione U. Para controlar todas as catapultas locais, pressione J.
Para controlar o próximo dragão, pressione I. Para controlar todos os dragões locais, pressione K.
Para controlar o próximo mago, pressione O. Para controlar todos os magos locais, pressione L.

Quando uma tecla faz você controlar a próxima unidade, a mesma tecla
combinada com Shift faz você controlar a unidade anterior. Por exemplo,
para controlar o operário anterior, pressione Shift + E.

Para controlar todas as unidades do mesmo tipo e no mesmo quadrado que a unidade atual, pressione 1.
Para controlar apenas a metade ou terço, pressione 2 ou 3.
Para parar de controlar um grupo, pressione 0.

Para controlar todas as unidades de combate locais, pressione S.
Para controlar todas as unidades de combate e operários, pressione Alt + S.

Quando uma tecla fazer você controlar um grupo de unidades locais, a
mesma tecla combinada com o Control faz você controlar um grupo de todo
o mapa. Por exemplo, para controlar todos os soldados, pressione Control R ou Control F.

Dando uma ordem (método principal)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para dar uma ordem à unidade controlada, o método principal consiste em
escolher a ordem numa lista e selecionar o alvo se a ordem pedir.

Para selecionar a ordem na lista, pressione A (e Shift A para a anterior).

Se você precisar escolher um alvo, pressione Tab (ou Shift Tab). Para
selecionar um quadrado remoto como alvo, use as setas.

Pressione Enter para confirmar sua escolha.

Dando uma ordem: método alternativo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Um segundo método de dar uma ordem consiste em selecionar um alvo com
Tab (ou as setas) e então apertar Backspace. A ordem padrão será dada.
Por exemplo, um operário com alvo numa mina de ouro irá explorá-la se
você apertar Backspace.

Dando uma ordem: usando atalhos
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para dar uma ordem com um atalho, pressione Alt + A. Uma mensagem vai
falar a lista de atalhos disponíveis para a unidade controlada.
Pressione o atalho e a ordem será executada imediatamente, a menos que
um alvo necessite ser selecionado.

Examinando a situação
^^^^^^^^^^^^^^^^^^^^^^^^^

Para saber que unidade (ou grupo) você controla, pressione Espaço.
Ademais, você se moverá ao quadrado ocupado pela unidade (ou pelo líder do grupo).

Para saber quanto de ouro você tem, pressione Z. Pressione X para a madeira e C para a comida.

Para saber a vida da unidade selecionada, pressione V.

Para examinar novamente um objeto selecionado com Tab, pressione Control.

Dando uma ordem sem cancelar as anteriores (enfileirando comandos)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Segure Shift antes de apertar enter para confirmar a ordem.

Também funciona para ordens padrões, use Shift antes de apertar
Backspace.

Pressione Espaço para verificar se a unidade tem várias ordens para executar.

Aqui está uma lista de situações que enfileirar ordens pode ajudar:

- Exemplo 1: você quer mandar um operári ir em todos os quadrados iniciais (para saber onde o inimigo está). Mova o cursor para um dos quadrados iniciais e pressione
  Shift Backspace. Repita para cada quadrado inicial
  e o operário irá se mover para um quadrado e em seguida irá para outro.

- Exemplo 2: você quer que um operário explore vários recursos. Selecione um recurso como alvo, pressione Shift + Backspace. Repita para cada recurso. Quando um
  recurso se esgotar, o operário irá explorar os próximos de sua lista de ordens.


Dando uma ordem imperativa
^^^^^^^^^^^^^^^^^^^^^^^^^^

Se você segurar o Control antes de pressionar Enter ou Backspace, a
ordem vai ser imperativa.

Unidades com uma ordem imperativa tendem a ignorar tudo que não é
relacionado à ordem. Se elas tiverem que ir em algum lugar e encontrarem
unidades inimigas, elas vão simplesmente ignorá-las.
Isso é arriscado na maioria das vezes mas em alguns casos pode ser útil,
por exemplo para focar-se num alvo muito importante.

Aqui estão algumas situações em que um comando imperativo pode ser útil:

- Exemplo 1: você quer que suas unidades ataquem uma construção ou unidade inimiga específica e ignorarem o resto. Selecione o alvo e aperte Control Backspace.
- Exemplo 2: você quer que suas unidades saiam de um quadrado e ignorem o inimigo. Selecione outro quadrado e pressione Control Backspace.

Você pode enfileirar ordens imperativas também. Segure Control + Shift
ao invés de Shift.

Atacando uma unidade amiga
^^^^^^^^^^^^^^^^^^^^^^^^^^

Selecione a unidade e pressione Shift Backspace: as unidades vão atacar
o alvo.

Exceção: se o alvo for uma construção danificada (ou uma unidade
reparável como a catapulta) e você controlar operários, eles vão reparar o alvo.

Bloqueando uma saída
^^^^^^^^^^^^^^^^^^^^

Introduzido na versão 1.2 alpha 10.

Para bloquear uma saída (caminho, ponte), você pode fazer qualquer uma dessas alternativas:
- ordenar uma unidade (ou várias) a bloquear a saída (dando a ordem "bloquear" ou usando back space com a saída como alvo);
- construir uma muralha nela;
- construir qualquer outra construção nela.

Uma unidade ou um portão deixará unidades amigas passarem.

Modo zoom (experimental)
^^^^^^^^^^^^^^^^^^^^^^^^

Novo na versão 1.2 alpha 10.

F8: entrar ou sair do modo zoom. Escape também sai.

O quadrado é dividido em 3 quadrados menores de 3 x 3. Um quadrado
com zoom pode ser usado como um alvo de uma ordem (ir a, essencialmente).

Grupos de controle
^^^^^^^^^^^^^^^^^^^^^^^^^

Novo em 1.2 alpha 10.

Control + 6, 7, 8 ou 9: configura o grupo 6, 7, 8 ou 9 com as unidades
controladas atualmente

Shift + 6, 7, 8 ou 9: adiciona as unidades controladas atualmente ao grupo 6, 7, 8 ou 9

6, 7, 8 ou 9: recupera o grupo 6, 7, 8 ou 9

Nos menus
^^^^^^^^^^^^

As setas funcionam também: Cima e Baixo para selecionar, Direita confirma, Esquerda cancela.

Pressione qualquer letra para selecionar o próximo item começando com essa letra.
Pressione Shift + qualquer letra para selecionar o item anterior começando com essa letra.

Outros comandos
^^^^^^^^^^^^^^^

F5 e F6: mensagem anterior / próxima no histórico.
Alt: interrompe a frase atual.

Para sair de uma partida ou acessar o menu, pressione F10. Alt F4 e Control C fazem o mesmo.

Control + Espaço: faz o jogo entrar no modo em primeira pessoa. Escape: volta para o modo mapa.

Home / End, + / - do teclado numérico: aumenta / diminui o volume geral do som.
Control Home / End, control + / - do teclado numérico: aumenta / diminui o volume relativo da voz.

F3: fala o tempo de jogo.
Control F3: sino em minuto ligado / desligado (desligado por padrão)

Control + Tab seleciona apenas bosques, minas de ouro, terrenos, e
alvos reparáveis ou construíveis (construções danificadas, terrenos de construção, catapultas danificadas...).

Alt + R resseleciona a ordem dada anteriormente. Útil para recrutar a mesma unidade ou construir o mesmo tipo de construção várias vezes.
Alt + G resseleciona a ordem dada anteriormente e a valida se não
precisar de alvo. Por exemplo, para recrutar 5 arqueiros adicionais,
pressione Alt + G 5 vezes.
Desde o SoundRTS 1.1 alpha 3, Alt + A faz a mesma coisa que Alt + G.

Apóstrofo (a tecla a baixo do Escape): comandos de console (apenas no modo offline).
No momento os comandos úteis são apenas add_units (para obter unidades
ou construções instantaneamente)
e victory (para ganhar, por exemplo para passar um capítulo). Exemplo
do comando "add_units": "add_units a1 100 archer". Novo no SoundRTS 1.2 alpha 9.

4. Jogos multijogador
---------------------

4.1 Iniciando um jogo multijogador
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Selecione multijogador e depois escolher o servidor numa lista.

Num servidor público, você poderá organizar um jogo.

Dica: enquanto você estiver esperando por jogadores, você pode executar
SoundRTS uma segunda vez para jogar offline. Quando alguém aparecer,
pressione F10 para pausar seu jogo e poder começar a jogar online.

4.2 Conversando
^^^^^^^^^^^^^^^

Você pode conversar na entrada do servidor, na sala de pré-jogo e
durante a partida. Todavia, o organizador está temporariamente indisponível
durante a seleção do mapa e da velocidade da partida.

Para conversar com todos da mesma sala, pressione F7, digite a mensagem
e pressione Enter.

Outra opção seria usar o Skype (ou algum programa similar) se você conhece os outros jogadores.

4.3 Jogo em equipe
^^^^^^^^^^^^^^^^^^

As equipes devem ser criadas antes que o jogo inicie. Elas não podem ser mudadas durante o jogo.

Jogadores aliados compartilham o conhecimento do mapa, a vitória, os
investimentos (novo no SoundRTS 1.2 alpha 9), e suas unidades podem se
ajudar. Um trabalhador pode usar um depósito do aliado (o recurso vai
ser adicionado à tropa do trabalhador).

Num jogo de servidor, os computadores não são aliados por padrão.

Nota: num jogo offline, os computadores são aliados.

Dica: para jogar com um computador como aliado, crie um servidor privado.

4.4 Como fazer com que seu servidor fique acessível a outros jogadores
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para verificar se seu servidor pode ser acessado fora de sua rede
local, espere alguém conectar, ou idealmente pergunte a um amigo se ele
pode se conectar de fora. Como uma última tentativa,
você pode tentar usar um serviço de teste de portas ( pesquise "port forwarding tester"
por exemplo). Tenha cuidado: eu não garanto que esse tipo de site não
seja malicioso!
O site não deve solicitar que você instale alguma ferramenta, por exemplo.

Em muitos casos você terá que configurar seu roteador para que ele envie
as conexões que entram no seu servidor na porta 2500 para seu computador da rede local.

Você poderá também ter que configurar o DHCP para que seu servidor tenha
sempre o
mesmo endereço IP na rede local.

Se você está usando um firewall, você também terá que liberar a porta 2500 nele.

Sobre os servidores padrão (o que não é executado pelo menu do
jogo):mesmo que seu servidor seja acessível de fora, em alguns casos
você não conseguirá conectar nele de sua rede local usando a lista de
servidores. A opção "Digite o endereço IP do servidor" funciona em
muitos casos, mas ela não significa que o servidor é acessível de fora.

4.5 Como baixar um mapa de um servidor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Jogue uma partida com o mapa que você quer baixar. Antes que o jogo
inicie, o mapa aparecerá na `pasta temporária`_ e ficará lá até que
outro mapa o sobrescreva. Dependendo do formato do mapa, pode ser um
arquivo de texto chamado recent_map.txt ou uma pasta chamada recent_map.

5. Elementos do jogo
--------------------

Comida
^^^^^^

O recrutamento de uma nova unidade só pode acontecer se o jogador tiver
comida suficiente. Se algumas fazendas forem destruídas ou novas
unidades forem obtidas sem recrutar, e
a comida vir a ser insuficiente, as unidades vão ser mantidas sem
nenhum problema. Entretanto, nenhum recrutamento vai ser permitido até
que o jogador consiga mais comida.

Investimento de tecnologia
^^^^^^^^^^^^^^^^^^^^^^^^^^

Os investimentos se aplicam à todas as unidades do jogador (atuais e futuras).

Unidades voadoras
^^^^^^^^^^^^^^^^^

Desde o SoundRTS 1.1, as unidades aéreas voam em linha reta até o
objetivo, ignorando o caminho terrestre.

Unidades invisíveis e detectoras
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para se defender de unidades invisíveis, existem pelo menos 3 maneiras.

- consiga uma unidade detectora (ou lance uma magia de detecção) e ataque a unidade invisível;
- Use uma magia de destruição de área no quadrado que contém a unidade;
- ignore a unidade invisível e destrua as construções rapidamente o suficiente.

6. Mais detalhes para personalização
------------------------------------

SoundRTS.ini
^^^^^^^^^^^^

Esse arquivo se localiza na `Pasta do usuário`_ . Ele contém vários
parâmetros sobre como o jogo trabalha. Quando SoundRTS inicia, se esse
arquivo contiver um erro, um novo será gerado tentando se recuperar a maior
quantidade de parâmetros do arquivo original.

Opções da linha de comando
^^^^^^^^^^^^^^^^^^^^^^^^^^

Pela linha de comando, a opção -h dá a lista de opções disponíveis.

A opção --mods sobrescreve a linha "mods =" do SoundRTS.ini_ . Por
exemplo, para iniciar SoundRTS com o soundpack e o mod orc: soundrts.exe --mods=soundpack,orc

Pacote de sons
^^^^^^^^^^^^^^

SoundRTS vem com um mod chamado "soundpack" contendo sons alternativos.
Para ativar esse mod, no SoundRTS.ini_ substitua a linha "mods =" com "mods = soundpack".
Então, reinicie o jogo para que as alterações tenham efeito.

wait_delay_per_character
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Como algumas vezes é difícil identificar quando um leitor de tela para de falar, uma solução
melhor-do-que-nada é calcular a duração de cada mensagem.
Então, um parâmetro adicional chamado "wait_delay_per_character" determina quanto tempo SoundRTS vai esperar até que ele envie outra mensagem ao leitor.
Com "wait_delay_per_character = .1" e uma mensagem de 10 caracteres, SoundRTS vai esperar por .1 * 10 = 1 segundo.

Aumente o valor de "wait_delay_per_character" se algumas mensagens estão sendo interrompidas pela próxima.
Diminua o valor de "wait_delay_per_character" se o jogo está silenciando muito entre uma mensagem e outra.

Pasta temporária
^^^^^^^^^^^^^^^^

A pasta temporária contém os logs e o mapa jogado pela última vez.

A pasta temporária está localizada na `pasta do usuário`_ com o nome de "tmp".

Pasta do usuário
^^^^^^^^^^^^^^^^

A pasta do usuário contém as configurações do jogo, os mapas
personalizados e mods, e a pasta temporária.
Uma forma fácil de achar a pasta do usuário é abrí-la pelo menu de opções.

Se a pasta principal do jogo tiver uma pasta denominada "user", então essa pasta vai ser a pasta do usuário.
Se a pasta "user" não existir, a pasta do usuário vai ser localizada dependendo do sistema operacional:

- Windows XP: "C:\\Documents and settings\\seu_nome_de_usuario\\Dados de aplicativos\\SoundRTS unstable"
- Linux: "home/seu_nome_de_usuario/.SoundRTS unstable"

Como criar uma versão portátil do SoundRTS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Desde o SoundRTS 1.0 beta 10 p, é possível ter todos os arquivos do jogo (log,
configuração, mapas personalizados...) dentro da pasta do jogo. Seguem
as instruções de como proceder para fazer isso:

- installe o SoundRTS
- Windows: copie a `pasta do jogo` de "Arquivos de programas" para
  uma pasta que você pode escrever (a área de trabalho, um drive USB, etc)

- na nova pasta do SoundRTS, crie uma pasta chamada "user". "user" pode
  ser uma cópia de uma `pasta do usuário`_ existente (porém a versão tem que ser a mesma).

- Windows: para jogar, execute "soundrts.exe".

Como mudar a velocidade padrão de jogos offline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Encontre SoundRTS.ini_ na `pasta do usuário`_ e modifique a linha "speed = ...". Use um número inteiro.

Mudando algumas teclas do jogo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Desde o SoundRTS 1.1, o layout de teclado está definido num arquivo
chamado "bindings.txt" na `pasta do jogo`.

Criando um app para Mac
^^^^^^^^^^^^^^^^^^^^^^^

Se você conseguiu instalar a versão multiplataforma para o Mac, talvez
você possa criar um app para facilitar a instalação para outros jogadores.
Seguem algumas dicas. Use py2app.
Você não precisa do código. Por exemplo, crie um arquivo chamado soundrts_launcher.py
contendo essa linha: "import soundrts".
Você também pode criar um arquivo chamado server_launcher.py com a linha: "import server".
Verifique se executar "soundrts_launcher.py" funciona.

Usando o instalador do Windows com uma conta limitada (Windows XP)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Você pode usar uma conta limitada para instalar SoundRTS. Escolha uma
pasta diferente da "Arquivos de programas".

Ainda que você instale SoundRTS com uma conta administradora, você pode jogar usando uma conta limitada.

O que faz um mapa multijogador ser oficial?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mapas oficiais não tocam nenhum som antes de seu título. Os mapas
multijogador oficiais são listados em cfg/official_maps.txt com
checksums para ter a certeza de que eles não foram modificados.

Como selecionar um idioma diferente?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Se cfg/language.txt estar vazio, o programa selecionará automaticamente o idioma do sistema.
Para selecionar um idioma específico, digite o código do idioma em cfg/language.txt,
por exemplo "en", "fr-ca", "pt" ou "pt-BR".
Verifique a pasta res para saber que códigos de idioma estão incluídos.

7. Créditos
-----------

Nota: essa lista não é exaustiva. Obrigado a todos que ajudaram!

O jogo foi escrito por SoundMUD (soundmud@gmail.com).

Descoberta da comunidade franca de jogos acessíveis de áudio, e ideias iniciais: Sabine Gorecki.
Inúmeros testes e encourajamentos durante o primeiro período do SoundMUD: Alex.
Primeiro teste do SoundMUD no Linux: Miguel.
Relançamento do projeto do SoundMUD, encorajamentos durante o segundo
período do SoundMUD para completar o jogo de estratégia, e inúmeros
testes: Louis-Rock Lampron et Martin Morin.

Tradução em Inglês: SoundMUD.
Tradução em Alemão: Alexander Westphal from Gameport.
Tradução em Italiano: Gabriel Battaglia.
Tradução em Espanhol: Alan.

Melhoras da voz em inglês e sons: Bryan Smart.

Mapa multijogador 101 - fronteira: Bryan Smart.

Notas finais do tradutor

Gostaria de agradecer a todo o pessoal da BGB Blind Games Brasil, que
traduziu o jogo até 2013, que foi quando eu comecei a traduzir. Vocês
merecem. Sem vocês eu nunca teria conhecido esse jogo, nem o teria
traduzido como fiz agora. Obrigado!
