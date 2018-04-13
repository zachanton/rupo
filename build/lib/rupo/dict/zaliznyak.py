import os
from rupo.g2p.phonemes import Phonemes


class ZalyzniakDict:
    @staticmethod
    def convert_to_accent_only(dict_file, accent_file):
        with open(dict_file, 'r', encoding='utf-8') as r:
            lines = r.readlines()
        with open(accent_file, 'w', encoding='utf-8') as w:
            for line in lines:
                for word in line.split("#")[1].split(","):
                    word = word.strip()
                    pos = -1
                    clean_word = ""
                    primary = []
                    secondary = []
                    for i, ch in enumerate(word):
                        if ch == "'" or ch == "`":
                            if ch == "`":
                                secondary.append(pos)
                            else:
                                primary.append(pos)
                            continue
                        clean_word += ch
                        pos += 1
                        if ch == "ё":
                            primary.append(pos)
                    if len(primary) != 0:
                        w.write(clean_word + "\t" + ",".join([str(a) for a in primary]) + "\t" +
                                ",".join([str(a) for a in secondary]) + "\n")

    @staticmethod
    def convert_to_g2p_only(dict_file, g2p_dict_path, g2p_model):
        from rupo.g2p.rnn import RNNG2PModel
        g2p_predictor = RNNG2PModel()
        g2p_predictor.load(g2p_model)
        with open(dict_file, 'r', encoding='utf-8') as r:
            lines = r.readlines()
        with open(g2p_dict_path, 'w', encoding='utf-8') as w:
            words = []
            for line in lines:
                for word in line.split("#")[1].split(","):
                    word = word.strip()
                    clean_word = ""
                    for i, ch in enumerate(word):
                        if ch == "'" or ch == "`":
                            continue
                        clean_word += ch
                    words.append(clean_word)
            phonetic_words = g2p_predictor.predict(words)
            for i, word in enumerate(words):
                w.write(word + "\t" + phonetic_words[i] + "\n")

    @staticmethod
    def convert_to_phoneme_stress(source_file, destination_file, g2p_dict_path, g2p_model):
        from rupo.g2p.rnn import RNNG2PModel
        from rupo.g2p.aligner import Aligner
        from rupo.stress.dict import StressDict
        g2p_predictor = RNNG2PModel(g2p_dict_path)
        g2p_predictor.load(g2p_model)
        aligner = Aligner()
        grapheme_stress_dict_path = os.path.join(os.path.dirname(os.path.abspath(source_file)), "ru_grapheme_stress.txt")
        ZalyzniakDict.convert_to_accent_only(source_file, grapheme_stress_dict_path)
        d = StressDict(raw_dict_path=grapheme_stress_dict_path)
        vowels = set(Phonemes.VOWELS)
        with open(destination_file, 'w', encoding='utf-8') as w:
            samples = 0
            for word, accents in d.get_all():
                primary_in_dict = [int(stress[0]) for stress in accents if stress[1] == StressDict.StressType.PRIMARY]
                secondary_in_dict = [int(stress[0]) for stress in accents if stress[1] == StressDict.StressType.SECONDARY]
                phonemes = g2p_predictor.predict([word])[0]
                g, p = aligner.align(word, phonemes)
                primary = ZalyzniakDict.align_stresses(g, p, primary_in_dict)
                secondary = ZalyzniakDict.align_stresses(g, p, secondary_in_dict)
                is_valid = True
                for stress in primary+secondary:
                    if p[stress] not in vowels:
                        print(g, p, stress, p[stress])
                        is_valid = False
                if is_valid:
                    w.write(phonemes + "\t" + ",".join([str(i) for i in primary]) + "\t" +
                            ",".join([str(i) for i in secondary]) + "\n")
                samples += 1
                if samples % 1000 == 0:
                    print(samples)

    @staticmethod
    def align_stresses(g, p, stresses):
        index = -1
        spaces_count = 0
        for i, stress in enumerate(stresses):
            for j in range(len(p)):
                if g[j] == " ":
                    spaces_count += 1
                else:
                    index += 1
                    if index == stress:
                        stresses[i] += spaces_count
        return stresses