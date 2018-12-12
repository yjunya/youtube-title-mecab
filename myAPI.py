import os
import re
import networkx as nx
import random
from mecab_pandas import MeCabParser
from apiclient.discovery import build
from flask import Flask, jsonify, abort, make_response
from flask_cors import CORS


# initial for check
kusa = re.compile(r'^[wWｗＷ]+$')
def is_kusa(s):
    return kusa.match(s) is not None
alnumReg = re.compile(r'^[a-zA-Z0-9]+$')
def isalnum(s):
    return alnumReg.match(s) is not None
isetu = re.compile(r'^い説$')
def is_isetu(s):
    return isetu.match(s) is not None

# initial for graph
G = None

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
        return make_response(jsonify(result))
    else:
        result.insert(0, random_word)
        result.pop(-1)
        return make_response(jsonify(result))

# words of search
@app.route('/search/<q>', methods=['GET'])
def search(q):
    #search query
    YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
    youtube = build('youtube','v3',developerKey=YOUTUBE_API_KEY)
    mp = MeCabParser()
    query = q

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
            if is_kusa(df['surface_form'][i]) == True:
                df['surface_form'][i] = "草(www)"

            if df['word_class'][i] == "名詞" and df['class_detail1'][i] != "非自立" and df['class_detail1'][i] != "数" and isalnum(df['surface_form'][i]) == False:
                if is_isetu(df['surface_form'][i]) == True:
                    df['surface_form'][i] = "説"

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

    final_result = {"words":result ,"categoryID":maxElem(categoryIDs) }
    return make_response(jsonify(final_result))


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

