#encoding = utf-8
#-*- coding: utf-8 -*-
import nltk
import csv
import os
import re
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet


# -*- coding: utf-8 -*-
import psycopg2

# 获得连接
conn = psycopg2.connect(
    database="cetus-dev",
    user="postgres",
    password="123456",
    host="127.0.0.1",
    port="5432",
)
# 获得游标对象
cursor = conn.cursor()


# np noun phrase
# pp prepositional phrase
# vp verb phrase


class NormalChunks:
    def __init__(self, content):
        # innoof就是介词，除了of
        self.grammar = r"""
        NP: {<DT>?<JJ|VBN|VBG>+<NN|NNS>+}
        PP: {<IN><NP>}   
        AVP: {<RB.*><VB.*>}    

        TV: {<TO|AVP><VB.*>}            
        VNP: {<VB.*><NP|PP|CLAUSE>+$} 
        VP: {<TV|VB.*|AVP><NP>}
        AJJ: {<RB.*>+<JJ>}
        JJIN: {<JJ>.*<IN>}

        RBIN: {<RB.*><IN>}
        DTNN: {<DT>?<NN|NNS>}
        VIN: {< DTNN|VB.*|NP>+.*<IN|TO>(<DT>?<NN|NNS|NP>)*}
        
        RBINNP: {<RBIN><NN.*|NP>}
        """
        # prepos 不加in的原因：因为in多半和后面组一个整体，所以前面不算
        self.content = content
        self.easywords = ["too", "so", "already", "very", "not", "yet"]
        self.be = [" is ", " are ", " am ", " was ", " were ", " being "]
        self.predisposal()

    def getChunks(self, parsedTree):
        res = []
        donotShow = ["TV", "DTNN"]
        for i in parsedTree:
            if type(i) != tuple:
                if i.label() in donotShow:
                    continue
                res.append((i.label(), self.traverse(i).strip()))
        return res

    def finalFilter(self, chunk):
        if chunk[0:2] == "of":
            return chunk[3:]
        return chunk

    def traverse(self, content):
        ret = ""
        for i in content:
            if type(i) == str:
                return i + " "
            else:
                ret += self.traverse(i)
        return ret

    def preprocess(self, sentences: str):
        sentenceTree = nltk.sent_tokenize(sentences)
        sentenceTree = [nltk.word_tokenize(sent) for sent in sentenceTree]
        sentenceTree = [nltk.pos_tag(sent) for sent in sentenceTree]
        return sentenceTree

    def getCohesion(self, sentence: str, row=0):

        grammar = r""" #单独匹配
            COM: {<,>?<.+>{2,5}<,>}
        """
        sentenceTree = self.preprocess(sentence)[row]
        regexp = nltk.RegexpParser(grammar, loop=2)
        parsedTree = regexp.parse(sentenceTree)
        return parsedTree

    def predisposal(self):  # 预处理，把一些问题去了
        self.content = self.content.replace("\n", " ")
        for i in self.easywords:
            self.content = self.content.replace(i, "")

        while self.content.find("  ") != -1:
            self.content = self.content.replace("  ", " ")

        for i in self.be:
            self.content = self.content.replace(i, " be ")

    def normalChunks(self, sentence: str, row=0):
        # try:
        if sentence.strip() == "":
            return [], ()

        sentenceTree = self.preprocess(sentence)[row]

        cp = nltk.RegexpParser(self.grammar, loop=2)
        res = self.getChunks(cp.parse(sentenceTree))

        pos = []  # 格式： [(0,1),(3,5)]
        FinalRet = []  # 用来返回最后的词块结果
        for i in res:
            phrase = self.finalFilter(i[1])  # 二次处理，防止出现太无用的词块
            start = self.content.find(phrase)
            if start == -1:
                print(sentence)
            end = start + len(phrase) - 1
            pos.append((start, end))
            FinalRet.append([i[0], phrase])

        return FinalRet, pos

    # except:
    #    return []

    def chunking(self):  # 输出成字符串形式
        out = ""
        for i in self.content.split("."):
            res, pos = self.normalChunks(i)
            if res != []:
                for j in res:
                    out += j[0] + " " + j[1] + "  "
                out += " " + str(pos)
                out += "\n"
        return out

    def chunking_json(self):  # 输出成json模式
        out = {}
        for i in self.content.split("."):
            tmp = []
            res, pos = self.normalChunks(i)
            if res != []:
                for index, ele in enumerate(res):
                    # res[index][0]是词块类型
                    # res[index][1]是词块
                    # pos[index][0] 是起始位置
                    # pos[index][1] 是结尾位置
                    if i in out:
                        out[i].append(
                            {
                                "type": res[index][0],
                                "content": res[index][1],
                                "posStart": pos[index][0],
                                "posEnd": pos[index][1],
                            }
                        )
                    else:
                        out[i] = [
                            {
                                "type": res[index][0],
                                "content": res[index][1],
                                "posStart": pos[index][0],
                                "posEnd": pos[index][1],
                            }
                        ]
        return out


class extractFromFiles:
    def __init__(self):
        dirs = os.listdir("./phrases")
        with open("./phrases/" + dirs[4], "r",encoding="utf-8") as f:
            reader = csv.reader(f)
            self.phraseTable = []
            for row in reader:
                self.phraseTable.append(row)
            self.wnl = WordNetLemmatizer()

    def analysisSentence(self, sentence):
        for i in self.phraseTable:
            con = i[0].replace("...", ".*")
            con = i[0].replace("be", "(be|are|is|was|were|am)")
            con = i[0].replace("one", ".+")
            con = i[0].replace("sth.", ".*")
            con = i[0].replace("sth", ".*")
            con = i[0].replace("sb.", ".*")
            con = i[0].replace("sb", ".*")
            con = ".*" + con + ".*"
            ret = re.match(con, sentence, re.IGNORECASE)

            if ret != None:
                print(i[0])


def write_into_db(contentjson, article):
    # 先新建一个词块库
    cursor.execute("select count(*) from chunkrepo;")
    chunkRepoID = cursor.fetchone()[0]
    print("ChunkRepoID: ", chunkRepoID)

    cursor.execute("select count(*) from sentence")
    sentenceID = cursor.fetchone()[0]


    chunkIDs = []
    cursor.execute("select count(*) from chunk;")
    chunkID = cursor.fetchone()[0]
    sentenceIDs = []
    for i in contentjson:
        sentence = i
        sentenceID += 1
        sentenceIDs.append(sentenceID)
        # -- 插入句子 -- 
        cursor.execute(
            "insert into sentence (sentence_id,content) values ("
            + str(sentenceID)
            + ",%s" 
            + ")"
            ,(sentence,)
        )
        # -- end --
        for j in contentjson[i]:

            attr = j['type']
            chunk = j['content']
            posStart = j['posStart']
            posEnd = j['posEnd']
            # -- 插入词块 --
            chunkID = chunkID + 1
            chunkIDs.append(chunkID)
            cursor.execute(
                "insert into chunk (chunk_id,content,pos_start,pos_end) values ("
                + str(chunkID)
                + ",%s,"
                + str(posStart) +','
                + str(posEnd)
                + ")" 
                , (chunk,)
            )
            # -- end --

            # -- 插入词块对应句子 --
            cursor.execute(
                "insert into chunk_sen_map (chunk_id,sentence_id) values("
                + str(chunkID)
                + ","
                + str(sentenceID)
                + ")"
            )


    # -- 插入词块库对应的词块 --
    cursor.execute(
        "insert into chunkrepo (chunkrepo_id,chunk_id_list) values("+str(chunkRepoID)+",ARRAY"
        + str(chunkIDs)
        + ") "
    )

    # -- end --

    # -- 插入文章 --
    cursor.execute("select count(*) from article")
    articleID = cursor.fetchone()[0]
    cursor.execute(
        "insert into article (article_id,title,content, sentence_pos_start,sentence_pos_end) values("
        + str(articleID)
        + ",%s,%s" 
        + ","
        + str(sentenceIDs[0]) +","
        + str(sentenceIDs[len(sentenceIDs)-1])
        + ") "
        , ("", article)
        
        
    )
    # -- end --

    conn.commit()

def delDB():
    cursor.execute("delete from chunk")
    cursor.execute("delete from chunkrepo")
    cursor.execute("delete from sentence")

    cursor.execute("delete from article")

    cursor.execute("delete from chunk_sen_map")


    conn.commit()

delDB()
dir = './语料库/四级-1/生物/'
for i in os.listdir(dir):

    f = open(dir+i, "r",encoding='utf-8')
    content = f.read()
    f.close()

    eff1 = extractFromFiles()
    normal = NormalChunks(content)
    out = normal.chunking_json()
    write_into_db(out,content)
