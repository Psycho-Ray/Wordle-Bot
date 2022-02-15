import re
import sys
from typing import List, Iterator

from botcity.web import WebBot, Browser


def char_range(c1, c2):
    for c in range(ord(c1), ord(c2)+1):
        yield chr(c)


class Bot(WebBot):
    def __init__(self):
        super().__init__()
        self.headless = False
        self.driver_path = "./chromedriver.exe"
        self.word_size = 5
        self.dictionary = self.load_dictionary()
        self.knowledge = {
            letter: {
                'Total Darkened': 0,
                'Total Golden': 0
            }
            for letter in char_range('A', 'Z')
        }

    def load_dictionary(self) -> List[str]:
        with open(self.get_resource_abspath('words_alpha.txt'), 'r') as file:
            return list(filter(lambda word: len(word) == self.word_size, file.read().splitlines()))

    def permanent_remove(self, word: str):
        # Removes the word from the current game's dictionary
        print("Permanently removing the word " + word + " from the dictionary")
        self.dictionary.remove(word)

        # Reloads the original dictionary
        with open(self.get_resource_abspath('words_alpha.txt'), 'r') as file:
            dictionary = file.read().splitlines()
            dictionary.remove(word)

        # Removes the word from the dictionary file
        with open(self.get_resource_abspath('words_alpha.txt'), 'w') as file:
            for line in dictionary:
                file.write(line + '\n')

        # Appends the removed word into the removed_words file
        with open(self.get_resource_abspath('removed_words.txt'), 'a') as file:
            file.write(word + '\n')

    def find_all_counter(self, label) -> int:
        return len([ele for ele in self.find_all(label, matching=0.985, waiting_time=100)])

    def action(self, execution=None):
        for self.word_size in reversed(range(4, 12)):
            # Resets the game dict
            self.dictionary = self.load_dictionary()
            self.knowledge = {
                letter: {
                    'Total Darkened': 0,
                    'Total Golden': 0
                }
                for letter in char_range('A', 'Z')
            }
            self.play_game()

    def play_game(self):
        # Opens the Hello Wordle game page
        self.browse("https://hellowordl.net/")

        # Adjust difficulty
        if self.word_size != 5 and self.find('size_adjustment', matching=0.90, waiting_time=10000):
            # Clicks on the word size slider
            self.click()

            # Types left to increase difficulty, types right to decrease it
            key = self.KEYS.ARROW_RIGHT if self.word_size > 5 else self.KEYS.ARROW_LEFT

            # Adjusts the difficulty
            for i in range(abs(self.word_size - 5)):
                self.kb_type(key)

        # For each of our 6 "lives"...
        for _ in range(6):
            # Plays a turn and checks for a game over
            if self.play_turn():
                print('Game Over: You WIN!')
                break

        # Checks for a game over
        if self.find('defeat', matching=0.90, waiting_time=1000):
            print('Game Over: You LOSE!')

        # Stop the browser and clean up
        self.wait(5000)
        self.stop_browser()

    def play_turn(self):
        # Attempts to use the fist valid word of the dictionary
        attempt = self.dictionary[0]
        self.paste(attempt)
        self.enter()

        # Checks for a game over
        if self.find('victory', waiting_time=500) or self.find('victory2', waiting_time=500):
            return True

        # If the word isn't valid...
        if self.find('not_valid', matching=0.90, waiting_time=1000):
            # Permanently removes it from the dictionary file
            self.permanent_remove(attempt)

            # Erases it from the game board
            for _ in range(self.word_size):
                self.backspace()

            # Keeps playing
            return self.play_turn()

        # For each letter of the word...
        for pos, letter in enumerate(attempt):
            # Init
            print(letter, end='')

            # Skip repeated letters
            if pos > attempt.find(letter):
                continue

            # Uses Computer Vision to count and locate info about the letters
            darkened = self.find_all_counter(letter + '_dark') - self.knowledge[letter]['Total Darkened']
            golden = self.find_all_counter(letter + '_golden') - self.knowledge[letter]['Total Golden']
            green = attempt.count(letter) - darkened - golden

            # Filters dark letters
            def dark_filter(word: str) -> bool:
                # If there is at least 1 darkened copy of 'A', we know exactly how many 'A's the word has
                if darkened > 0:
                    return word.count(letter) == attempt.count(letter) - darkened

                # Otherwise, we only know its minimum amount of 'A's
                return word.count(letter) >= attempt.count(letter)

            # Filters golden letters
            def golden_filter(word: str) -> bool:
                # If there are only green 'A's, we know their position. Otherwise, we don't
                if darkened > 0 or green > 0:
                    return True

                # The word must not have the golden letters in a position different than the one they appeared in
                for repeated in re.finditer(letter, attempt):
                    if word[repeated.start()] == letter:
                        return False

                return True

            # Filters green letters
            def green_filter(word: str) -> bool:
                # If there are only green 'A's, we know their position. Otherwise, we don't
                if darkened > 0 or golden > 0:
                    return True

                # The word must have the green letters in the position they appeared
                for repeated in re.finditer(letter, attempt):
                    if word[repeated.start()] != letter:
                        return False

                return True

            # Applies the filters
            self.dictionary = list(filter(dark_filter, self.dictionary))
            self.dictionary = list(filter(golden_filter, self.dictionary))
            self.dictionary = list(filter(green_filter, self.dictionary))

            # Updates our knowledge base
            self.knowledge[letter]['Total Darkened'] += darkened
            self.knowledge[letter]['Total Golden'] += golden

        print()
        print(list(self.dictionary))
        return False


if __name__ == '__main__':
    Bot.main()
