import os
import networkx as nx
import random
from mecab_pandas import MeCabParser
from apiclient.discovery import build
from flask import Flask, jsonify, abort, make_response


G = None

#import useMecab

# Flask
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
# HTTP GET
@app.route('/random')
def random_select():
    global G
    if G == None:
        G = nx.read_edgelist('result', delimiter=',', nodetype=str)

    ans = nx.pagerank(G,0.9)

    ans = [[key,value] for key, value in ans.items()]
    ans = sorted(ans, key=lambda x: x[1], reverse=True)

    #print(ans[random.randint(0,num-1)][0])
    random_word = random.choice(ans)[0]

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

    ans2 = []
    for i in range(number):
        ans2.append(ans[i][0])

    result = random.sample(ans2,4)

    if random_word in result:
        result.remove(random_word)
        result.insert(0, random_word)
        return make_response(jsonify(result))
    else:
        result.insert(0, random_word)
        result.pop(-1)
        return make_response(jsonify(result))


@app.route('/search/<q>', methods=['GET'])
def search(q):
    YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
    youtube = build('youtube','v3',developerKey=YOUTUBE_API_KEY)
    mp = MeCabParser()
    query = q

    search_response = youtube.search().list(
        part='snippet',
        q=query,
        type='video',
        maxResults=1
    ).execute()

    for item in search_response['items']:
        title = item['snippet']['title']

        try:
            df = mp.parse(title)
        except:
            continue

        word_of_movie = []

        for i in range(len(df)):
            word_of_movie.append(df['surface_form'][i])

    return make_response(jsonify(word_of_movie))
#    kusa = re.compile(r'^[wWｗＷ]+$')
#    def is_kusa(s):
#        return kusa.match(s) is not None
#
#    alnumReg = re.compile(r'^[a-zA-Z0-9]+$')
#    def isalnum(s):
#        return alnumReg.match(s) is not None
#
#    isetu = re.compile(r'^い説$')
#    def is_isetu(s):
#        return isetu.match(s) is not None
#
#    mp = MeCabParser()
#
#    with open('test_sample', mode='r') as fr:
#
#        with open('test_result', mode='w') as fw:
#
#            line = fr.readline()
#
#            while line:
#                try:
#                    df = mp.parse(line)
#                except:
#                    line = fr.readline()
#                    continue
#
#                line = fr.readline()
#
#                word_of_movie = []
#
#                for i in range(len(df)):
#                    if is_kusa(df['surface_form'][i]) == True:
#                        df['surface_form'][i] = "草(www)"
#
#                    if df['word_class'][i] == "名詞" and df['class_detail1'][i] != "非自立" and df['class_detail1'][i] != "数" and isalnum(df['surface_form'][i]) == False:
#
#                        if is_isetu(df['surface_form'][i]) == True:
#                            df['surface_form'][i] = "説"
#
#                        word_of_movie.append(df['surface_form'][i])
#
#                if len(word_of_movie) > 1:
#                    for word in list(itertools.combinations(word_of_movie, 2)):
#                        fw.write("{},{}\n".format(word[0],word[1]))
#
#    return make_response(jsonify("test"))


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/')
def index():
    return 'Hello!'

# bashで叩いたかimportで入れたかを判定する
if __name__ == '__main__':
    app.run()

