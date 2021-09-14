from request import RequestBuildModel
import re
# esta porqueria tendria que venir por la linea de comandos, pero bueno
filename = "../user_defines.h"


def getFile():
    return open(filename, "r+")


def appendInfoToFile(_file, index, data):
    _file.insert(index, data)
    return _file


def save(_file, path):
    with open(path, "w") as f:
        f.writelines(_file)


def WriteUserDefine(data: RequestBuildModel):
    requestParams = data.__dict__
    textToAppend = ''
    for param in requestParams:
        if getattr(data, param) != None:
            undef = f'#undef {param}'
            define = f'#define {param} {getattr(data, param)}'
            textToAppend += undef + '\n' 
            textToAppend += define + '\n\n'
            print(define)

    if textToAppend:
        textData = '\n#define True true \n'
        textData += '#define False false \n\n'
        textData += textToAppend

        regex = re.compile(r'(.+){{USER_DEFINES_END}}')

        textFile = getFile()
        fileIndex = 0
        for line in textFile:
            if re.match(regex, line):
                fileIndex += 1
                break
            fileIndex += 1
        textFile.close()

        # file stuff:

        textFileW = getFile().readlines()
        appendInfoToFile(textFileW, fileIndex, textData)
        save(textFileW, filename)
    return
