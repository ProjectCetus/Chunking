import nltk
import csv
import os
import re
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

# np noun phrase
# pp prepositional phrase
# vp verb phrase
f = open("./holmes/nava.txt", "r")
content = f.read()
f.close()

document = content


class NormalChunks:
    def __init__(self, content):
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
        Prepos: {of|to|towards|with|about|for}
        VIN: {< DTNN|VB.*|NP>+.*<Prepos|TO>(<DT>?<NN|NNS|NP>)*}
        
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

    def predisposal(self):
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
        for i in res:
            start = self.content.find(i[1])
            if start == -1:
                print(sentence)
            end = start + len(i[1]) - 1
            pos.append((start, end))

        return res, pos

    # except:
    #    return []

    def chunking(self):
        out = ""
        for i in self.content.split("."):
            res, pos = self.normalChunks(i)
            if res != []:
                for j in res:
                    out += j[0] + " " + j[1] + "  "
                out += " " + str(pos)
                out += "\n"
        return out


class extractFromFiles:
    def __init__(self):
        dirs = os.listdir("./phrases")
        with open("./phrases/" + dirs[4], "r") as f:
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


eff1 = extractFromFiles()
normal = NormalChunks(content)
out = normal.chunking()

f = open("report.txt", "w")
f.write(out)
f.close()
