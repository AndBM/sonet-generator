import pronouncing as pnc
import os
import markovify
import config
import string
import syllabifyARPA as ARPA
import re
from multiprocessing import Pool
import sys # For debugging exit
import random

#TODO: Implement new rhyming method
#TODO: Allow lines with more than 9 syllables
#TODO: Handle accidental rhymes (check in-code TODOs)
#TODO: Don't regenerate the model every time.
#TODO: Handle case of rhymes only appearing once to handle delta field

class Sonnet_crown:
    """An autogenerated crown of sonnets. If the base poem has n lines, there will be
    n sonnets and one master sonnet"""

    def __init__(self, base_pattern, prev_master=None):
        """Generate master sonnet"""
        self.config = config.Config()
        is_test = self.config.is_test

        all_text = ''
        for file in os.listdir(self.config.markovify_input_dir):
            if os.path.isdir(file):  # skip folders
                continue
            with open(self.config.markovify_input_dir + file,
                      encoding='utf-8') as f:
                all_text += f.read()
        self.text_model = markovify.Text(all_text)

        self.pattern = base_pattern
        # Count number of lines in sonnet
        self.line_number = len(''.join(i for i in base_pattern if not i.isdigit()))

        # Initialize list of subsonnets
        self.subsonnets = [None] * self.line_number

        # Generate master sonnet if not given
        if prev_master == None:
            self.master = Poem(base_pattern, self.text_model)
        else:
            self.master = prev_master

        self.master_lines = self.master.poem.split('\n')

    def generate_single_sonnet(self, line):
        """Generate a single sub-sonnet of the master sonnet starting with line
        and ending with line + 1"""
        print('Generating sonnet from line ' + str(line))
        start_line = self.master_lines[line]
        if line == self.line_number-1:
            # Check if we need to loop back to first line:
            end_line = self.master_lines[0]
        else:
            end_line = self.master_lines[line+1]

        poem = Poem(self.pattern, self.text_model, start_line, end_line)
        return poem

    def generate_full(self):
        """Generate a full sonnet crown"""
        #TODO: Parallelize this
        if self.config.parallel_poems:
            print('Hello')
            p = Pool()
            self.subsonnets = p.imap( self.generate_single_sonnet, range(self.line_number) )
        else:
            for i in range(self.line_number):
                self.subsonnets[i] = self.generate_single_sonnet(i)

    def print_full(self):
        """Print the full sonnet crown with subsonnets first and master last"""
        print(self.subsonnets)

        for i in range(self.line_number):
            if self.subsonnets[i] == None:
                print("\n-- Subsonnet missing --")
            else:
                self.subsonnets[i].print_poem()

        self.master.print_poem()

class Poem:
    """An auto-generated poem with lines based on the text corpus stated in the
    config file. A rhyme pattern argument can be passed for the constructor."""

    def __init__(self, pattern='ABAB6767', model=None, *args):
        self.config = config.Config()

        if model is None:
            # Generate text model
            all_text = ''
            for file in os.listdir(self.config.markovify_input_dir):
                if os.path.isdir(file):  # skip folders
                    continue
                with open(self.config.markovify_input_dir + file,
                          encoding='utf-8') as f:
                    all_text += f.read()
            self.text_model = markovify.Text(all_text)
        else:
            self.text_model = model

        # Now generate the poem
        self.poem = self.generate_poem(pattern, *args)

    def generate_poem(self, pattern, *args):
        """Generate a poem with a rhyme and syllable pattern as followed in the argument,
        e.g 'ABAB5757'. Upper and lower case letters are differentiated. For lines
        which should not necessarily rhyme, '_' should be passed, e.g. 'AA_BB55755'
        where there third line will not be part of a rhyme pattern."""

        #TODO: Allow better pattern with ABAB-5-7-5-7, counting non-digit chars and taking
        # half the number, then splitting with character - and ignoring first element

        # Ensure even number of input
        assert len(pattern) % 2 == 0, "Number of input characters must be even!"

        # There might be single letters from sonnet structure. Handle them.
        line_num = len(''.join(i for i in pattern if not i.isdigit()))
        singles = [i for i in pattern if pattern.count(i) == 1 and not i.isdigit()]
        for i in singles:
            pattern = pattern.replace(i,'_')

        # Set up basic objects of the poem as a dict object. Syntax:
        # Line ( line number, rhyme group, syllables, sentence )
        lines = [{'index': i, 'rhyme': pattern[i], 'syls': pattern[line_num+i], 'sent': None}
                 for i in range(line_num)]

        # Input lines from master sonnet if necessary
        # (ugly hack because iterables are hard)
        first_line = True
        for master_line in args:
            if first_line:
                lines[0]['sent'] = master_line
                first_line = False
            else:
                lines[line_num-1]['sent'] = master_line

        line_pairings = {c: [] for c in pattern[0:line_num-1] if not c == '_'}

        for rhyme in line_pairings:
            line_pairings[rhyme] = [l for l in lines if l['rhyme'] == rhyme]
        non_rhymes = [l for l in lines if l['rhyme'] == '_']
        final_lines = []

        # Build each group in parallel
        if self.config.parallel_groups:
            p = Pool()
            #accidental_rhymes = 0
            #while accidental_rhymes is not None:
            if self.config.is_test:
                for group in p.imap( self._build_group_TEST, line_pairings.values() ):
                    final_lines += group
            else:
                for group in p.imap( self._build_group, line_pairings.values() ):
                    final_lines += group

        #TODO: Implement smart rewriting of accidental rhyme lines. Legacy code:
                        # Rhyme found! Ensure that it is different from other groups
                        # already_used = False
                        # for prev_sent in final_lines:
                        #     if is_rhyme_pair(prev_sent['sent'], group[current]['sent']):
                        #         already_used = True
                        #         print("Rhyme already used, trying something else.")
                        # if not already_used:
                        #     rhyme_attempts = 0
                        #     current += 1
        else:
            if self.config.is_test:
                for group in line_pairings.values():
                    final_lines += self._build_group_TEST(group)
            else:
                for group in line_pairings.values():
                    # # Check for accidental rhymes
                    # while True:
                    new_group = self._build_group(group)
                    #     for prev_sent in final_lines:
                    #         if is_rhyme_pair(prev_sent['sent'], new_group[0]['sent']):
                    #             print("Rhyme already used, trying something else.")
                    #             already_used = True
                    #     if not already_used:
                    #         break
                    final_lines += new_group


        # Put whatever on the non-rhyming line
        # TODO: make sure they don't accidentally rhyme with any rhyme pairs
        for line in non_rhymes:
            line['sent'] = self._new_sentence(line['syls'])
            while line['sent'] == None:
                line['sent'] = self._new_sentence(line['syls'])

        # Run through final lines, check if any accidental rhymes

        # If _ rhyme, just try again

        # If non-_ rhyme, check if fixed group

        # If no fixed group, add one to list of accidental rhymes

        # If fixed group, add the other one to accidental rhymes

        # If no accidental rhymes, exit
            #accidental_rhymes = None

        # Sort the rhymes into the desired structure

        final_lines += non_rhymes
        final_lines.sort(key=lambda x: x['index'])

        return '\n'.join(line['sent'] for line in final_lines)

    def print_poem(self):

        #length = max(len(line) for line in self.poem.split('\n'))

        #print('*' * length)
        #print('-' * length)
        print("\n")
        print(self.poem)
        #print('-' * length)
        #print('*' * length)

    def _build_group(self,group):
        self.config = config.Config()
        max_tries_per_sent = self.config.max_rhyme_attempts
        n_lines = len(group)

        print('Looking for rhymes for ' + group[0]['rhyme'] + ' group.')

        if group[0]['sent'] is not None:
            # Allow no resets
            sent_fixed = 1
        elif group[n_lines-1]['sent'] is not None:
            # Allow no resets, remember that it was the last line
            sent_fixed = 2
            # Move last line to first line
            hold = group[0]
            group[0] = group[n_lines-1]
            group[n_lines-1] = hold
        else:
            # Create first sentence in the group
            sent_fixed = False
            group[0]['sent'] = self._new_sentence(group[0]['syls'])
            while group[0]['sent'] == None:
                group[0]['sent'] = self._new_sentence(group[0]['syls'])

        # Track how many lines we've finished
        current = 1

        # Prepare iteration to find rhymes
        rhyme_attempts = 0
        n_animation_dots = 0

        # INFINITE LOOP WOOO LET'S GO
        while True:
            if current == n_lines:
                # If we have all the rhymes needed, move on to the next rhyme group
                break

            if rhyme_attempts % int(max_tries_per_sent/10) == 0:
                #print('\r' + str(rhyme_attempts) )
                # Fancy animation
                n_animation_dots += 1
                print('\r' + n_animation_dots * '.', end='')
                if n_animation_dots == 20:
                    n_animation_dots = 0

            rhyme_attempts += 1
            if rhyme_attempts > max_tries_per_sent and not sent_fixed:
                print("\nTried more than max times, restarting group\n")
                # Restart from first sentence in group
                group[0]['sent'] = self._new_sentence(group[0]['syls'])
                while group[0]['sent'] == None:
                    group[0]['sent'] = self._new_sentence(group[0]['syls'])
                current = 1
                rhyme_attempts = 0

            # Generate next line
            group[current]['sent'] = self._new_sentence(group[current]['syls'])
            while group[current]['sent'] == None:
                # Keep trying until you get actual sentence
                group[current]['sent'] = self._new_sentence(group[current]['syls'])

            # Flexibly check if the line rhymes
            if is_rhyme_pair(group[0]['sent'], group[current]['sent']):
                print("Rhyme found!")
                current += 1

        print()  # animation on new line

        if sent_fixed == 2:
            # Switch the lines back
            hold = group[0]
            group[0] = group[n_lines-1]
            group[n_lines-1] = hold

        return group

    def _build_group_TEST(self,group):
        test_lines = ["This is a test", "I am the best", "This poem will end", "If you press send"
                      , "This is a nest","Nothing will bend","I am at rest","A lender will lend"]
        #group[0]['sent'] = random.choice(test_lines)

        max_tries_per_sent = self.config.max_rhyme_attempts
        n_lines = len(group)

        print('Looking for rhymes for ' + group[0]['rhyme'] + ' group.')

        if group[0]['sent'] is not None:
            # Allow no resets
            sent_fixed = 1
        elif group[n_lines-1]['sent'] is not None:
            # Allow no resets, remember that it was the last line
            sent_fixed = 2
            # Move last line to first line
            hold = group[0]
            group[0] = group[n_lines-1]
            group[n_lines-1] = hold
        else:
            # Create first sentence in the group
            sent_fixed = False
            group[0]['sent'] = random.choice(test_lines)

        # Track how many lines we've finished
        current = 1

        # Prepare iteration to find rhymes
        rhyme_attempts = 0
        n_animation_dots = 0

        # INFINITE LOOP WOOO LET'S GO
        while True:
            if current == n_lines:
                # If we have all the rhymes needed, move on to the next rhyme group
                break

            if rhyme_attempts % int(max_tries_per_sent/10) == 0:
                #print('\r' + str(rhyme_attempts) )
                # Fancy animation
                n_animation_dots += 1
                print('\r' + n_animation_dots * '.', end='')
                if n_animation_dots == 20:
                    n_animation_dots = 0

            rhyme_attempts += 1
            if rhyme_attempts > max_tries_per_sent and not sent_fixed:
                print("\nTried more than max times, restarting group\n")
                # Restart from first sentence in group
                group[0]['sent'] = self._new_sentence(group[0]['syls'])
                while group[0]['sent'] == None:
                    group[0]['sent'] = self._new_sentence(group[0]['syls'])
                current = 1
                rhyme_attempts = 0

            # Generate next line
            group[current]['sent'] = random.choice(test_lines)

            # Flexibly check if the line rhymes
            if is_rhyme_pair(group[0]['sent'], group[current]['sent']):
                print("Rhyme found!")
                current += 1

        print()  # animation on new line

        if sent_fixed == 2:
            # Switch the lines back
            hold = group[0]
            group[0] = group[n_lines-1]
            group[n_lines-1] = hold

        return group

    def _new_sentence(self,syls):
        """Create sentence with Markovify, check that it has correct number of syllables,
        return type None if this fails."""

        syls = int(syls)
        sent = self.text_model.make_short_sentence(
            syls * self.config.poem_avg_char_per_syl,
            tries=100,
            max_overlap_ratio=self.config.markovify_max_overlap_ratio,
            max_overlap_total=self.config.markovify_max_overlap_total
        )

        if sent == None:
            return None

        # Might be double work checking for punctuation
        sentNoPunctuation = sent[0:-1]
        try:
            phones = [pnc.phones_for_word(p)[0] for p in sentNoPunctuation.split()]
        except IndexError:
            # Word not found in dictionary
            phones = []

        if sum([pnc.syllable_count(p) for p in phones]) != syls or not sent:
            return None
        else:
            return ''.join(c for c in sent if c not in string.punctuation)

def rhyme_degree(target_word, test_word):
    """Returns a number between 0 and 1 as the degree of rhyming between two
    words, with 1 being an exact rhyme and 0 being no similarity at all."""

    if test_word in pnc.rhymes(target_word):
        print('\rFound rhyme pair from the pronouncing library:')
        print(target_word, 'and', test_word)
        return 1

    # extract word part from last stressed syllable excluding that syll's onset
    rhymes = {target_word: None, test_word: None}
    for word in rhymes:
        try:
            # get pronounciation for word
            pron = pnc.phones_for_word(word)[0]
        except IndexError:  # in case one of the words is not in the dictionary
            return 0
        # get stress pattern and find last stressed syllables
        stress = pnc.stresses(pron)
        last_stress = max([stress.rfind('1'), stress.rfind('2')])
        try:
            sylls = ARPA.syllabifyARPA(pron, return_list=True)
        except ValueError:  # in case the word cannot be syllabified
            return 0
        sylls = sylls[last_stress:]
        first_onset = re.split(ARPA.VOWELS_REGEX, sylls[0])[0]
        sylls[0] = sylls[0].replace(first_onset, '', 1)
        rhymes[word] = sylls

    # test for matching vowels and consonant clusters in onset and coda
    # the stressed vowel weighs double
    phones = 1 + max([sum(len(syll.split()) for syll in rhyme)
                      for rhyme in rhymes.values()])
    matches = 0
    for target_syll, test_syll in zip(rhymes[target_word], rhymes[test_word]):
        target_vowel = [phone for phone in target_syll.split()
                        if re.match(ARPA.VOWELS_REGEX, phone)][0]
        test_vowel = [phone for phone in test_syll.split()
                      if re.match(ARPA.VOWELS_REGEX, phone)][0]
        target_clusters = target_syll.split(target_vowel)
        test_clusters = test_syll.split(test_vowel)
        # measure match of syllable onsets
        matches += len(
            set(target_clusters[0].strip().split()).intersection(
                set(test_clusters[0].strip().split())
            )
        )
        # measure match of vowels
        if target_vowel[:2] == test_vowel[:2]:  # test for the vowel itself
            matches += 1
            # test for similar stress
            if (target_vowel[-1] in ['1', '2']
                    and target_vowel[-1] == test_vowel[-1]):
                matches += 1
        # measure match of syllable codas
        matches += len(
            set(target_clusters[1].strip().split()).intersection(
                set(test_clusters[1].strip().split())
            )
        )
    degree = matches / phones
    if degree > 0.7:
        print('\rFound rhyme pair with a rhyming degree of: ', degree)
        print(rhymes)
    return degree

def is_rhyme_pair(target_line, test_line, same_allowed=False, min_degree=0.8):
    """Return true if the passed lines rhyme."""

    # avoid later problems from empty or None lines
    if (not target_line or target_line == ''
            or not test_line or test_line == ''):
        return False

    # get the last words from the lines
    target_last = target_line.split()[-1]
    test_last = test_line.split()[-1]

    if target_last.lower() == test_last.lower() and not same_allowed:
        return False

    # TODO: take short words into account: combine short words and see if they
    # can constitute one phonological word, i.e. one stress unit
    degree = rhyme_degree(target_last, test_last)
    if degree > min_degree:
        return True
    else:
        return False

#poem = Poem('ABABCDCDEFEGFG76767676767676')
#poem.print_poem()
sonnet_crown = Sonnet_crown('ABCB7676')
#sonnet_crown.generate_single_sonnet(0)
sonnet_crown.generate_full()
sonnet_crown.print_full()
