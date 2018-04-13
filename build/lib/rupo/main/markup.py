# -*- coding: utf-8 -*-
# Автор: Гусев Илья
# Описание: Модуль для описания разметки по ударениям и слогам.

import json
from typing import List, Set
import xml.etree.ElementTree as etree

from dicttoxml import dicttoxml

from rupo.util.preprocess import get_first_vowel_position
from rupo.util.mixins import CommonMixin
from rupo.main.tokenizer import Tokenizer, Token
from rupo.util.timeit import timeit


class Annotation(CommonMixin):
    """
    Класс аннотации.
    Содержит начальную и конечную позицию в тексте, а также текст аннотации.
    """
    def __init__(self, begin: int, end: int, text: str) -> None:
        self.begin = begin
        self.end = end
        self.text = text


class Syllable(Annotation):
    """
    Разметка слога. Включает в себя аннотацию и номер слога, а также ударение.
    Если ударение падает не на этот слог, -1.
    """
    def __init__(self, begin: int, end: int, number: int, text: str, stress: int=-1) -> None:
        super(Syllable, self).__init__(begin, end, text)
        self.number = number
        self.stress = stress

    def vowel(self) -> int:
        """
        :return: позиция гласной буквы этого слога в слове (с 0).
        """
        return get_first_vowel_position(self.text) + self.begin

    def from_dict(self, d: dict) -> 'Syllable':
        self.__dict__.update(d)
        if "accent" in self.__dict__:
            self.stress = self.__dict__["accent"]
        return self


class Word(Annotation):
    """
    Разметка слова. Включает в себя аннотацию слова и его слоги.
    """
    def __init__(self, begin: int, end: int, text: str, syllables: List[Syllable]) -> None:
        super(Word, self).__init__(begin, end, text)
        self.syllables = syllables

    def count_stresses(self) -> int:
        """
        :return: количество ударений в слове.
        """
        return sum(syllable.stress != -1 for syllable in self.syllables)

    def stress(self) -> int:
        """
        :return: последнее ударение в слове, если нет, то -1.
        """
        stress = -1
        for syllable in self.syllables:
            if syllable.stress != -1:
                stress = syllable.stress
        return stress

    def get_stressed_syllables_numbers(self) -> List[int]:
        """
        :return: номера слогов, на которые падают ударения.
        """
        return [syllable.number for syllable in self.syllables if syllable.stress != -1]

    def get_stresses(self) -> Set[int]:
        """
        :return: все ударения.
        """
        stresses = set()
        for syllable in self.syllables:
            if syllable.stress != -1:
                stresses.add(syllable.stress)
        return stresses

    def set_stresses(self, stresses: List[int]) -> None:
        """
        Задать ударения, все остальные убираются.

        :param stresses: позиции ударения в слове.
        """
        for syllable in self.syllables:
            if syllable.vowel() in stresses:
                syllable.stress = syllable.vowel()
            else:
                syllable.stress = -1

    def get_short(self) -> str:
        """
        :return: слово в форме "текст"+"последнее ударение".
        """
        return self.text.lower() + str(self.stress())

    def from_dict(self, d: dict) -> 'Word':
        self.__dict__.update(d)
        syllables = d["syllables"]  # type: List[dict]
        self.syllables = [Syllable(0, 0, 0, "").from_dict(syllable) for syllable in syllables]
        return self

    def to_stressed_word(self):
        from rupo.stress.word import StressedWord, Stress
        return StressedWord(self.text, set([Stress(pos, Stress.Type.PRIMARY) for pos in self.get_stresses()]))

    def __hash__(self) -> int:
        """
        :return: хеш разметки.
        """
        return hash(self.get_short())


class Line(Annotation):
    """
    Разметка строки. Включает в себя аннотацию строки и её слова.
    """
    def __init__(self, begin: int, end: int, text: str, words: List[Word]) -> None:
        super(Line, self).__init__(begin, end, text)
        self.words = words

    def from_dict(self, d) -> 'Line':
        self.__dict__.update(d)
        words = d["words"]  # type: List[dict]
        self.words = [Word(0, 0, "", []).from_dict(word) for word in words]
        return self

    def count_vowels(self):
        num_vowels = 0
        for word in self.words:
            for syllable in word.syllables:
                if get_first_vowel_position(syllable.text) != -1:
                    num_vowels += 1
        return num_vowels


class Markup(CommonMixin):
    """
    Класс данных для разметки в целом с экспортом/импортом в XML и JSON.
    """
    def __init__(self, text: str=None, lines: List[Line]=None) -> None:
        self.text = text
        self.lines = lines
        self.version = 2

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def from_json(self, st) -> 'Markup':
        d = json.loads(st)
        return self.from_dict(d)

    def from_dict(self, d) -> 'Markup':
        self.__dict__.update(d)
        lines = d["lines"]  # type: List[dict]
        self.lines = [Line(0, 0, "", []).from_dict(line) for line in lines]
        return self

    def to_xml(self) -> str:
        """
        Экспорт в XML.

        :return self: строка в формате XML
        """
        return dicttoxml(self.to_dict(), custom_root='markup', attr_type=False).decode('utf-8').replace("\n", "\\n")

    def from_xml(self, xml: str) -> 'Markup':
        """
        Импорт из XML.

        :param xml: XML-разметка
        :return self: получившийся объект Markup
        """
        root = etree.fromstring(xml)
        if root.find("version") is None or int(root.find("version").text) != self.version:
            raise TypeError("Другая версия разметки")
        lines_node = root.find("lines")
        lines = []
        for line_node in lines_node.findall("item"):
            words_node = line_node.find("words")
            words = []
            for word_node in words_node.findall("item"):
                syllables_node = word_node.find("syllables")
                syllables = []
                for syllable_node in syllables_node.findall("item"):
                    stress_node = syllable_node.find("accent") \
                        if syllable_node.find("accent") is not None \
                        else syllable_node.find("stress")
                    stress = int(stress_node.text)
                    syllables.append(Syllable(int(syllable_node.find("begin").text),
                                              int(syllable_node.find("end").text),
                                              int(syllable_node.find("number").text),
                                              syllable_node.find("text").text,
                                              stress))
                words.append(Word(int(word_node.find("begin").text), int(word_node.find("end").text),
                                  word_node.find("text").text, syllables))
            lines.append(Line(int(line_node.find("begin").text), int(line_node.find("end").text),
                              line_node.find("text").text, words))
        self.text = root.find("text").text.replace("\\n", "\n")
        self.lines = lines
        return self

    def from_raw(self, text: str) -> 'Markup':
        """
        Импорт из сырого текста с ударениями в конце слов

        :param text: текст.
        :return: разметка.
        """

        pos = 0
        lines = []
        for line in text.split("\n"):
            if line == "":
                continue
            line_tokens = []
            for word in line.split(" "):
                i = -1
                ch = word[i]
                stress = ""
                while ch.isdigit() or ch == "-":
                    stress += ch
                    i -= 1
                    ch = word[i]
                line_tokens.append((word[:i+1], int(stress[::-1])))
            words = []
            line_begin = pos
            for pair in line_tokens:
                token = pair[0]
                stress = pair[1]
                from rupo.g2p.graphemes import Graphemes
                syllables = Graphemes.get_syllables(token)
                for j in range(len(syllables)):
                    syllables[j].begin += pos
                    syllables[j].end += pos
                word = Word(pos, pos + len(token), token, syllables)
                word.set_stresses([stress])
                words.append(word)
                pos += len(token) + 1
            lines.append(Line(line_begin, pos, " ".join([pair[0] for pair in line_tokens]), words))
        self.text = "\n".join([line.text for line in lines])
        self.lines = lines
        return self

    @staticmethod
    @timeit
    def process_text(text: str, stress_predictor) -> 'Markup':
        """
        Получение начального варианта разметки по слогам и ударениям.

        :param text: текст для разметки
        :param stress_predictor: предсказатель ударений.
        :return markup: разметка по слогам и ударениям
        """
        from rupo.g2p.graphemes import Graphemes
        begin_line = 0
        lines = []
        words = []
        text_lines = text.split("\n")
        for text_line in text_lines:
            tokens = [token for token in Tokenizer.tokenize(text_line) if token.token_type == Token.TokenType.WORD]
            for token in tokens:
                word = Word(begin_line + token.begin, begin_line + token.end, token.text,
                            Graphemes.get_syllables(token.text))
                # Проставляем ударения.
                stresses = stress_predictor.predict(token.text.lower())
                # Сопоставляем ударения слогам.
                if len(word.syllables) > 1:
                    word.set_stresses(stresses)
                words.append(word)
            end_line = begin_line + len(text_line)
            lines.append(Line(begin_line, end_line, text_line, words))
            words = []
            begin_line = end_line + 1
        return Markup(text, lines)
