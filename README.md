# POC-KafkaConnect
Este repositório tem por objetivo realizar uma POC utilizando o Kafka Connect ([Confluent Platform](https://developer.confluent.io/)), validando sua captura de dados de um banco de dados Postgres e registrando essa captura em uma tabela do Google Big Query.

## Setup do banco de dados
Essa POC utilizará um banco de dados Postgres. O banco de dados pode ser obtido facilmente utilizando a sua [imagem](https://hub.docker.com/_/postgres) Docker. 

Para baixar e configurar a imagem em um container diretamente via terminal, execute esse comando:

`docker run -d --name postgresql-container -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres postgres`

Após executar o comando, o container com o banco de dados já estará rodando e disponível para acesso em: http://localhost:5432

Para os testes de CDC, é preciso criar uma ou mais tabelas no banco de dados para simular transações. [Aqui](scripts/create_tables.sql) está disponibilizado um script que já popula algunmas tabelas com dados de uma livraria fictícia. Também é necessário executar esse select no banco de dados para alterar o WAL LEVEL (nível de log gerado pelo Postgres), pois o Kafka Connect precisa de no mínimo um WAL LEVEL = `logical`.

`ALTER SYSTEM SET wal_level = logical;`

Reinicie o container para que a configuração possa ser aplicada na inicialização do banco de dados. Para validar se o WAL LEVEL está com o valor correto, execute:

`SHOW wal_level;`

Com o banco de dados rodando e com dados inseridos, seguimos para a configuração do Kafka Connect CE.

## Setup Kafka Connect - Confluent Platform
O passo-a-passo abaixo está seguindo os passos desse [link](https://docs.confluent.io/platform/current/platform-quickstart.html#step-1-download-and-start-cp
), utilizando o "Tar Archive˜. Para utilizar o arquivo .tar, é preciso que sua máquina tenha certos [pré-requisitos](https://docs.confluent.io/platform/current/platform-quickstart.html#prerequisites). **É possível também utilizar a imagem Docker disponibilizada, ao final desse README, há um tópico específico para a instalação dos containers utilizando Docker.**

Execute os comandos conforme o passo-a-passo do link acima e será criado um serviço presente em http://localhost:9021/ onde teremos o Confluent Platform rodando.

Para realizar as integrações e validar o CDC é necessário baixar alguns plugins no [Confluent Hub](https://www.confluent.io/hub/).
### Plugin Debezium Postgresql

Para capturar as mensagens de transações de um banco de dados Postgresql utilizando o Kafka Connect será utilizado o plugin [Debezium PostgreSQL CDC Source Connector](https://www.confluent.io/hub/debezium/debezium-connector-postgresql). Baixe o pacote zip e insira o conteúdo na pasta `share/confluent-hub-components` do seu Confluent Platform instalado anteriormente. Sugiro essa pasta pois para capturar plugins o Confluent Platform utiliza um parâmetro `plugin.path` dentro de um arquivo localizado em `etc/schema-registry` e na configuração padrão do Confluent Platform essa é a pasta de plugins padrão.

### Plugin BigQuery
Para realizar o envio das mensagens capturadas pelo Kafka Connect para uma tabela no Google Big Query, é necessário baixar o plugin [Google BigQuery Sink Connector](https://www.confluent.io/hub/wepay/kafka-connect-bigquery). Baixe o pacote zip e insira o conteúdo na pasta `share/confluent-hub-components` do seu Confluent Platform instalado anteriormente. Sugiro essa pasta pois para capturar plugins o Confluent Platform utiliza um parâmetro `plugin.path` dentro de um arquivo localizado em `etc/schema-registry` e na configuração padrão do Confluent Platform essa é a pasta de plugins padrão.

Caso esteja utilizando Docker, será necessário inserir os arquivos no volume do container, nas mesmas pastas descritas acima.

⚠ APÓS O DOWNLOAD SERÁ NECESSÁRIO REINICIAR TODOS OS SERVIÇOS DO CONFLUENT PLATFORM ⚠ 

`confluent local services stop`

`confluent local services start`

Após reiniciar o Confluent Platform, os connectors instalados devem ser exibidos em Connect > connect-default > Add connector com os nomes `PostgresConnector` e `BigQuerySinkConnector`.

**A partir daqui, a configuração utilizando Docker ou o arquivo .tar são iguais, pois utilizam o confluent platform diretamente**

## Gerando mensagens de transações no banco de dados
Acesse o Confluent em http://localhost:9021/. Navegue em Connect > connect-default > Add connector.
Caso tenha seguido os passos para setup do banco de dados exatamente como este documento, basta utilizar [este](connectors/connector_postgres_config.json) arquivo clicando em `Upload connector config file` para configurar o seu connector. Ele basicamente é um JSON com as informações básicas de conexão ao banco Postgres e alguns parâmetros de conexão para o Kafka Connect. Caso tenha seu próprio banco de dados, basta alterar os parâmetros abaixo:

| Parâmetro | Informações |
| --- | --- |
| database.hostname | IP do banco de dados. | 
| database.port | Porta do banco de dados. |
| database.user | Usuário do para acesso ao banco de dados. |
| database.password | Senha do usuário. | 
| database.dbname | Nome do banco de dados. |

Aguarde alguns instantes até o connector iniciar (ele pode apresentar falha em primeiro instante). Os tópicos serão criados seguindo o nome das tabelas no banco de dados e já estarão ouvindo as tabelas caso alguma transação seja feita. Ao navegar até o menu `Topics`, selecionar um tópico e clicar em `Messages`, caso haja qualquer transação dentro da tabela, a mesma será capturada em tempo real e apresentada em tela.

Exemplo de tópicos criados:

![topics](lib/topics.png)

Exemplo de mensagens em um tópico (aparecerão apenas mediante a movimentação nas tabelas):

![messages](lib/messages.png)

## Capturando mensagens e registrando no BigQuery
Acesse o Confluent em http://localhost:9021/. Navegue em Connect > connect-default > Add connector.
No caso do BigQuery, precisaremos configurar manualmente o arquivo de configuração por conta da Google Service Account, projeto e dataset do Google que irão mudar de acordo com quem está fazendo os testes. [Aqui](connectors/connector_BigQuery_config.json) temos um exemplo de arquivo de configuração. Deverão ser alterados os parâmetros abaixo:

| Parâmetro | Informações |
| --- | --- |
| topics | Tópico(s) que o Sink Connector deve enviar ao BQ. | 
| project | Projeto do GCP selecionado para receber os dados. |
| defaultDataset | Dataset selecionado para receber os dados. |
| keyfile | Localização da Google Service Account. |

Aguarde alguns instantes até o connector iniciar (ele pode apresentar falha em primeiro instante). As tabelas no Big Query serão criadas seguindo o nome dos tópicos inseridos no arquivo de configuração. As mensagens passadas serão automáticamente enviadas para a tabela do BQ, além de que qualquer nova mensagem será enviada, assim registrando as mudanças na tabela.

![bigquery](lib/bigquery.png)

### Service Account via Carol
Para gerar uma service account pela Carol, basta acessar o menu de Tenant Admin > Tokens > Google Service Account. Com o arquivo baixado, utilize a localização do mesmo dentro de sua máquina (caso esteja seguindo este passo-a-passo) ou insira o mesmo no volume do Docker para que o container consiga visualizar o arquivo.

## Visualizando o fluxo de CDC
1. Acesse o tópico que irá monitorar para os testes, navegue até o menu `Messages`.
2. Insira/Altere/Delete um registro em uma das tabelas criadas. [Aqui](scripts/postgresadddata.py) temos um script que popula mil linhas na tabela `Sales` cada vez que é executado.
3. Uma mensagem aparecerá na tela de visualização de mensagens do tópico (Kafka Connect capturando a transação do banco de dados).
4. Acesse o console do Google Big Query, no projeto e dataset configurados anteriormente. Verifique a tabela com o nome do tópico, a alteração estará presente como uma nova linha.

O arquivo [postgres_public_Users.xlsx](./postgres_public_Users.xlsx) tem os dados gerados no BigQuery pelo CDC configurado. Além disso, a tabela do BigQuery pode ser acessada diretamente na tenant e tabela `bca1007e136a4632a83dabd97879684c.postgres_public_Users`.

## Utilizando Docker
Para criar a mesma estrutura utilizando Docker, basta utilizar o arquivo [docker-compose.yml](./docker-compose.yml) presente neste repositório, ele é disponibilizado pelo próprio Confluent na página de [Quick Start](https://docs.confluent.io/platform/current/platform-quickstart.html#step-1-download-and-start-cp) e pode ser baixado usando o comando abaixo:

`curl --silent --output docker-compose.yml https://raw.githubusercontent.com/confluentinc/cp-all-in-one/7.3.1-post/cp-all-in-one/docker-compose.yml`

Após baixar o arquivo, basta executar o Docker Compose:

`docker-compose up -d`

Os containers serão inicializados e irão subir o serviço nas portas padrões conforme anteriormente, ou seja, o serviço será acessado novamente por http://localhost:9021/ onde teremos o Confluent Platform rodando. É importante ressaltar que para subir os containers, deve-se parar todos os serviços locais do confluent (caso tenha instalado localmente sem usar docker), digitando o comando `confluent local services stop` no terminal.

Com os containers rodando, precisaremos adicionar os plugins baixados nos passos `Plugin Debezium Postgresql` e `Plugin BigQuery`. Baixe ambos os .zip e execute os seguintes comandos:

`docker cp wepay-kafka-connect-bigquery-2.4.2 **ID_DO_CONTAINER**:/usr/share/java`

`docker cp debezium-debezium-connector-postgresql-2.0.1 **ID_DO_CONTAINER**:/usr/share/java`


Substitua **ID_DO_CONTAINER** pelo id do container de nome `connect` que foi criado ao executar o docker-compose.yml.

![messages](lib/connect.png)

Reinicie o container (pode ser apenas o `connect` ou todos os containers).

Os connectors irão aparecer no menu Connect > connect-default > Add connector.

Agora com os connectors instalados, basta utilizar os arquivos de configuração da pasta `connectors` para configurar os connectors e seguir com a configuração do CDC. 

Sugiro voltar aos tópicos anteriores caso seja necessário um passo a passo mais detalhado. 

OBS: A configuração utilizando apenas Docker (banco de dados + Confluent Platform) exige algumas configurações de networking para que os containers possam se comunicar, além de que o banco de dados deverá estar habilitado para aceitar conexões TCP/IP externas. 

## HTTP Sink Connector
Para realizar a inserção de registros pelo intake da Carol (e não diretamente por uma tabela no BigQuery por exemplo) precisaremos utilizar um HTTP Sink Connector. Esse tipo de connector irá ouvir um tópico dentro do Kafka Connect e assim que mensagens forem sendo geradas, o mesmo irá enviar uma request HTTP/HTTPS para a URL especificada em seu arquivo de configuração.

Foram testados dois Sink Connectors:

[Confluent HTTP Sink Connector](https://www.confluent.io/hub/confluentinc/kafka-connect-http)

[Asaintsever Kafka Connect HTTP Sink Connector](https://asaintsever.github.io/kafka-connect-http-sink/)

O arquivo de configuração de cada um está em:

[Confluent HTTP Sink Connector - config file](./connectors/connector_HttpSink_confluent_config.json)

[Asaintsever Kafka Connect HTTP Sink Connector - config file](./connectors/connector_HttpSink_asaintsever_config.json)

Os arquivos contém configurações básicas de cada connector, afim de enviar uma mensagem com schema específico para o intake da Carol. Para utilizá-los, deve-se gerar um access_token via `https://api.carol.ai/api/v1/oauth2/token` e verificar se a URL está correta (org, tenant, staging, connector da Carol).

Os connectores se comportam de maneiras semelhantes, porém o [Asaintsever Kafka Connect HTTP Sink Connector](https://asaintsever.github.io/kafka-connect-http-sink/) teve um comportamento mais direto e com menos percalços do que o [Confluent HTTP Sink Connector](https://www.confluent.io/hub/confluentinc/kafka-connect-http). Já o [Confluent HTTP Sink Connector - config file](./connectors/connector_HttpSink_config.json) possui mais opções de modos de autenticação, apesar de ter apresentado diversos erros de timeout e rebalancing do cluster durante os testes (entendo que esses erros podem ser diminuidos com ajustes mais finos na configuração).

Para validar o funcionamento do sink connector isoladamente, foi criado um tópico chamado `ingestion_newstaging`. Esse tópico irá receber a mensagem abaixo, que irá popular uma staging na Carol com dois campos, `stagingid` e `stagingstring`.

{
  "stagingid": 1,
  "stagingstring": "abcrd"
}

Veja que a mensagem é exatamente o Json recebido pelo intake da Carol para uma staging com esses dois campos. É importante que o corpo da mensagem tenha o formato aceito pela Carol, caso não esteja em um formato suportado, os registros serão rejeitados e não inseridos na staging.

Para produzir essa mensagem manualmente, basta ir até o tópico e clicar em `Produce a new message to this topic`. Cole o Json acima e envie a mensagem. Após alguns segundos o registro deve aparecer na staging da Carol.

Ambos os connectors foram capazes de enviar a mensagem para a staging, mostrando que se a mensagem enviada na request estiver no formato correto, será aceita pela Carol e processada.

![staging](lib/staging.png)

Uma observação importante é que caso seja o intuito utilizar as mensagens vindas de outro connector (exemplo Postgres), é necessário configurar a formatação da mensagem, pois ao chegar na Carol sem a formatação correta, os registros são rejeitados por serem considerados dados inválidos. O objeto de teste foi validar se os Sink Connectors do Kafka podem enviar dados para a Carol.

Comando para verificar os logs do cluster localmente:
confluent local services connect log

