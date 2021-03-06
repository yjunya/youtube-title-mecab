import os
import re
import networkx as nx
import random
from mecab_pandas import MeCabParser
from apiclient.discovery import build
from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS


# initial for check
laughReg = re.compile(r'^([wWｗＷ]+|草(www))$')
def isLaugh(s):
    return laughReg.match(s) is not None
alnumReg = re.compile(r'^[a-zA-Z0-9]+$')
def isAlnum(s):
    return alnumReg.match(s) is not None
theoryReg = re.compile(r'^(説|い説|る説)$')
def isTheory(s):
    return theoryReg.match(s) is not None
kanaLetterReg = re.compile(r'^[ぁ-んァ-ヴｦ-ﾟ]$')
def isKanaLetter(s):
    return kanaLetterReg.match(s) is not None

# initial for graph
G = None

#initial for youtube
youtube = None

# listのもっとも多い要素を返す
def maxElem( lis ):
  '''
  与えられたリストの中に、最も多く存在する要素を返す
  (最大の数の要素が複数ある場合、pythonのsetで先頭により近い要素を返す)
  '''
  L = lis[:]#copy
  S = set(lis)
  S = list(S)
  MaxCount=0
  ret='nothing...'

  for elem in S:
    c=0
    while elem in L:
      ind = L.index(elem)
      foo = L.pop(ind)
      c+=1
    if c>MaxCount:
      MaxCount=c
      ret = elem
  return ret

# initial Flask
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

# words of random
@app.route('/random')
def random_select():
    global G
    if G == None:
        G = nx.read_edgelist('result', delimiter=',', nodetype=str)

    random_word = random.choice(list(G.nodes))

    personalization_dict = {}
    name = [random_word]
    number = 100

    for key in G:
        personalization_dict[key] = 0
        for i in name:
            if key == i:
                personalization_dict[key] = 1

    ans = nx.pagerank(G=G, alpha=0.9, personalization=personalization_dict)

    ans = [[key,value] for key, value in ans.items()]
    ans = sorted(ans, key=lambda x: x[1], reverse=True)

    result = [i[0] for i in random.sample(ans[0:number],4)]

    if random_word in result:
        result.remove(random_word)
        result.insert(0, random_word)
    else:
        result.insert(0, random_word)
        result.pop(-1)

    final_result = {"words":result ,"categoryId":"0" }
    return make_response(jsonify(final_result))

# words of search
@app.route('/search', methods=['GET'])
def search():
    #search query
    global youtube
    if youtube == None:
        YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
        youtube = build('youtube','v3',developerKey=YOUTUBE_API_KEY)
    mp = MeCabParser()
    query = request.args.get('word')

    search_response = youtube.search().list(
        part='snippet',
        q=query,
        type='video',
        maxResults=10
    ).execute()

    word_of_movie = []
    movieIDs = []
    movieIDs_text = ""

    for item in search_response['items']:
        # get_movieIDs for get category
        movieIDs.append(item['id']['videoId'])
        title = item['snippet']['title']

        try:
            df = mp.parse(title)
        except:
            continue

        for i in range(len(df)):
            if df['word_class'][i] == "名詞" and df['class_detail1'][i] != "非自立" and df['class_detail1'][i] != "数" and df['class_detail1'][i] != "接尾" and df['class_detail1'][i] != "代名詞" and df['class_detail1'][i] != "接続詞的" and isAlnum(df['surface_form'][i]) == False and isLaugh(df['surface_form'][i]) == False and isKanaLetter(df['surface_form'][i]) == False and isTheory(df['surface_form'][i]) == False:
                word_of_movie.append(df['surface_form'][i])

    #create graph H
    H = nx.Graph()
    for word in word_of_movie:
        if word != query:
            H.add_edge(query,word)

    #combine graph
    global G
    if G == None:
        G = nx.read_edgelist('result', delimiter=',', nodetype=str)

    F = nx.compose(G,H)

    #personalized pagerank for query
    personalization_dict = {}
    number = 50

    for key in F:
        personalization_dict[key] = 0
        if key == query:
            personalization_dict[key] = 1

    ans = nx.pagerank(G=F, alpha=0.9, personalization=personalization_dict)

    ans = [[key,value] for key, value in ans.items()]
    ans = sorted(ans, key=lambda x: x[1], reverse=True)

    result = [i[0] for i in random.sample(ans[0:number],4)]

    if query in result:
        result.remove(query)
        result.insert(0, query)
    else:
        result.insert(0, query)
        result.pop(-1)

    # get_category
    for movieID in movieIDs:
        movieIDs_text += movieID
        movieIDs_text += ","

    search_response = youtube.videos().list(
        part='snippet',
        id=movieIDs_text
    ).execute()

    categoryIDs = []

    for item in search_response['items']:
        categoryIDs.append(item['snippet']['categoryId'])

    final_result = {"words":result ,"categoryId":maxElem(categoryIDs) }
    return make_response(jsonify(final_result))

# get movie
@app.route('/movie', methods=['GET'])
def get_movie():

    words = request.args.getlist('words')

    query = ""
    for word in words:
        query += word
        query += " "

    YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
    youtube = build('youtube','v3',developerKey=YOUTUBE_API_KEY)

    movieIDs = []

    search_response = youtube.search().list(
        part='id',
        q=query,
        type='video',
        maxResults=5,
    ).execute()

    for item in search_response['items']:
        movieIDs.append(item['id']['videoId'])

    result = {"url":movieIDs }

    return make_response(jsonify(result))

# error
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/')
def index():
    return 'Hello!'

# bashで叩いたかimportで入れたかを判定する
if __name__ == '__main__':
    app.run()

