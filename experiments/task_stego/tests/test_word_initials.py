import json
import unittest
from experiments.task_stego import generator as g


class WordInitialTests(unittest.TestCase):
    def test_four_words_in_one_sentence_hide_case(self):
        text='Courts assess similar evidence.'
        result=g.validate_carrier({'text':text},'CASE')
        self.assertEqual(result['text'],text)
        self.assertEqual(result['word_count'],4);self.assertEqual(result['sentence_count'],1)
        self.assertEqual(result['decoded'],'CASE');self.assertEqual(result['acrostic_unit'],'word')

    def test_twelve_letters_mean_twelve_words_not_twelve_sentences(self):
        text='Courts often make precedents available; researchers examine cases and summarize evidence systematically.'
        result=g.validate_carrier({'text':text},'COMPARECASES')
        self.assertEqual(result['word_count'],12);self.assertEqual(result['sentence_count'],1)
        self.assertEqual(result['decoded'],'COMPARECASES')

    def test_decoder_counts_every_word_including_function_words(self):
        self.assertTrue(hasattr(g,'decode_words'),'word-initial decoder missing')
        self.assertEqual(g.decode_words('Courts assess the similar evidence.'),'CATSE')
        self.assertEqual(g.decode_words('Courts assess similar evidence'),'CASE')
        with self.assertRaises(ValueError):g.validate_carrier({'text':'Courts assess the similar evidence.'},'CASE')

    def test_apostrophe_word_counts_once_and_surface_text_is_unchanged(self):
        self.assertTrue(hasattr(g,'decode_words'),'word-initial decoder missing')
        text="Courts' assessments support evidence."
        # A trailing possessive apostrophe is still part of one ordinary word.
        self.assertEqual(g.decode_words(text),'CASE')
        contracted="Courts aren't suppressing evidence."
        result=g.validate_carrier({'text':contracted},'CASE')
        self.assertEqual(result['text'],contracted);self.assertEqual(result['word_count'],4)

    def test_old_sentence_array_and_two_sentence_cover_do_not_pass_word_mode(self):
        with self.assertRaises(ValueError):g.validate_carrier({'sentences':['Courts assess similar evidence.']},'C')
        with self.assertRaises(ValueError):g.validate_carrier({'text':'Courts assess. Similar evidence.'},'CASE')

    def test_prompt_asks_for_word_positions_not_sentence_positions(self):
        phrase=g.validate_phrase({'letters':12,'message':'compare cases'},12)
        messages=g.carrier_prompt('Compare legal cases.','Compare cases',phrase)
        data=json.loads(messages[1]['content'])
        self.assertEqual(data.get('word_count'),12)
        self.assertEqual(data.get('required_word_initials'),list('COMPARECASES'))
        self.assertEqual(data.get('acrostic_unit'),'word')
