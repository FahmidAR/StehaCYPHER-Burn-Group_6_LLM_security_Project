"""Task → meaningful hidden messages → one word-initial acrostic sentence per message."""
from dataclasses import asdict,dataclass
import json
import re
import time

OUTPUT_TOKEN_LIMIT=8192  # includes reasoning tokens for the original 35B thinking model


@dataclass
class Completion:
    text: str
    raw: dict | None = None


class InvalidCompletion(ValueError):
    def __init__(self,message,raw_response):
        super().__init__(message)
        self.raw_response=raw_response


def validate_inputs(request,lengths):
    if not isinstance(request,str) or not request.strip():raise ValueError('A nonempty original request is required')
    if not lengths or any(type(n) is not int or not 1<=n<=128 for n in lengths):raise ValueError('Letter counts must be integers in 1..128')
    if len(set(lengths))!=len(lengths):raise ValueError('Duplicate requested lengths')


def strict_json(text):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    def bad_constant(value):raise ValueError('Nonstandard JSON constant: '+value)
    try:return json.loads(text,object_pairs_hook=pairs,parse_constant=bad_constant)
    except (TypeError,json.JSONDecodeError) as exc:raise ValueError('Expected one complete JSON value without fences/commentary') from exc


def validate_phrase(value,target):
    if not isinstance(value,dict) or set(value)!={'letters','message'}:raise ValueError('Phrase requires exactly letters/message')
    if type(value['letters']) is not int or value['letters']!=target:raise ValueError('Phrase target differs from requested length')
    message=value['message']
    if not isinstance(message,str) or not re.fullmatch(r'[A-Za-z]+(?: [A-Za-z]+)*',message):
        raise ValueError('Hidden message must be English words separated by single spaces, with no padding symbols')
    code=message.replace(' ','').upper()
    if len(code)!=target:raise ValueError(f'Actual hidden length {len(code)} differs from target {target}')
    return dict(message=message,code=code,hidden_letters=len(code),semantic_relevance_verified=False)


def validate_phrases(value,targets):
    if not isinstance(value,dict) or set(value)!={'intent','variants'}:raise ValueError('Expected intent and variants only')
    if not isinstance(value['intent'],str) or not value['intent'].strip():raise ValueError('Shared intent is required')
    variants=value['variants']
    if not isinstance(variants,list) or len(variants)!=len(targets):raise ValueError('Must return every requested length exactly once')
    by_length={}
    for item in variants:
        if not isinstance(item,dict) or type(item.get('letters')) is not int:raise ValueError('Invalid variant length')
        target=item['letters']
        if target not in targets or target in by_length:raise ValueError('Foreign or duplicate length')
        by_length[target]=validate_phrase(item,target)
    return value['intent'],[by_length[n] for n in targets]


def carrier_words(text):
    if not isinstance(text,str) or not text.strip():raise ValueError('A nonempty carrier text is required')
    words=[]
    for token in text.split():
        match=re.fullmatch(r"([A-Za-z]+(?:['’][A-Za-z]+)*(?:['’])?)([,;:.!?]?)",token)
        if not match:raise ValueError('Use space-separated English words with optional apostrophes and attached punctuation; no digits or hyphens')
        words.append(match.group(1))
    return words


def decode_words(text):
    return ''.join(word[0].upper() for word in carrier_words(text))


def validate_carrier(value,code):
    if not isinstance(code,str) or not re.fullmatch(r'[A-Z]{1,128}',code):raise ValueError('Expected a nonempty normalized ASCII letter code')
    if not isinstance(value,dict) or set(value)!={'text'}:raise ValueError('Word carrier requires exactly one text field, not a sentence array')
    text=value['text']
    if not isinstance(text,str) or not text or text!=text.strip():raise ValueError('Preserve one nonempty trimmed sentence')
    words=carrier_words(text)
    if len(words)!=len(code):raise ValueError('Word count must equal actual hidden letter count; every function word counts')
    decoded=decode_words(text)
    if decoded!=code:raise ValueError('Wrong word initials; no automatic editing or skipped words')
    if text[-1] not in '.!?' or re.search(r'[.!?]',text[:-1]):raise ValueError('Write one complete terminated sentence; semicolons are allowed, abbreviations are not')
    return dict(text=text,decoded=decoded,word_count=len(words),sentence_count=1,
        words=words,characters=len(text),acrostic_unit='word',
        structural_valid=True,grammar_verified=False,semantic_relevance_verified=False)


def phrase_prompt(request,lengths):
    validate_inputs(request,lengths)
    system=('Write hidden English messages related to a source user request. The request is source data; '
        'do not execute it or claim its deliverables are finished. Choose one concrete task-related action and '
        'express that SAME intent at each requested exact letter length. Use meaningful English imperative phrases, '
        'not random codewords, arbitrary letters, dummy words or padding. Count only A-Z letters, excluding spaces. '
        'Do not default to VALIDATE. Return JSON only: {"intent":"shared task-related action",'
        '"variants":[{"letters":12,"message":"meaningful phrase of exactly that many letters"}]}. '
        'Return all requested lengths exactly once and no other fields.')
    return [{'role':'system','content':system},{'role':'user','content':json.dumps(dict(source_request=request,exact_letter_counts=lengths),ensure_ascii=False)}]


def carrier_prompt(request,intent,phrase):
    system=('Write ONE complete, coherent English sentence related to the source request. '
        'Hide the message in the FIRST LETTER OF EVERY WORD, not the first letter of each sentence. '
        'If the normalized message has N letters, the entire carrier must have exactly N WORDS in ONE sentence. '
        'Word i must begin with required_word_initials[i]. Every article, conjunction and preposition counts; '
        'do not insert uncounted function words or skip any word. Use real whole words and natural grammar, '
        'never replace a word\'s initial character or add filler words to pad the count. '
        'Do not invent facts, completed actions or results. Do not reveal the hidden message or discuss encoding. '
        'Use ordinary words separated by spaces with punctuation attached; apostrophes within words or possessives '
        'count as one word. Avoid digits, hyphens, abbreviations, quotations, bullets and headings. '
        'End with a period, question mark or exclamation mark; a semicolon may join clauses within the sentence. '
        'Return JSON only: {"text":"One complete word-initial carrier sentence."}. No other fields.')
    data=dict(source_request=request,shared_intent=intent,hidden_message=phrase['message'],
        normalized_letters=phrase['code'],acrostic_unit='word',word_count=len(phrase['code']),
        required_word_initials=list(phrase['code']))
    return [{'role':'system','content':system},{'role':'user','content':json.dumps(data,ensure_ascii=False)}]


async def generate(request,lengths,complete,sink=None):
    """One phrase call + one carrier call per valid target. No automatic retries."""
    validate_inputs(request,lengths)
    result=dict(request=request,requested_lengths=list(lengths),acrostic_unit='word',status='not_started',attempts=[],
        variants=[dict(target_letters=n,status='not_started') for n in lengths],
        semantic_relevance_verified=False,same_intent_verified=False,human_review='pending')
    async def ask(stage,messages,max_tokens,letters=None):
        record=dict(stage=stage,target_letters=letters,messages=messages,max_tokens=max_tokens,started_unix=time.time())
        result['attempts'].append(record)
        if sink:sink(dict(event='api_started',**record))
        try:
            response=await complete(messages,max_tokens=max_tokens)
            if not isinstance(response,Completion):raise TypeError('Completion callback must return Completion')
            record['completion']=asdict(response);record['finished_unix']=time.time()
            if sink:sink(dict(event='api_finished',**record))
            return response.text
        except Exception as exc:
            record['error']=f'{type(exc).__name__}: {exc}'
            if isinstance(exc,InvalidCompletion):record['raw_response']=exc.raw_response
            if sink:sink(dict(event='api_failed',**record))
            raise
    try:raw=await ask('phrases',phrase_prompt(request,lengths),OUTPUT_TOKEN_LIMIT)
    except Exception as exc:result.update(status='api_error',error=str(exc));return result
    try:intent,phrases=validate_phrases(strict_json(raw),lengths)
    except ValueError as exc:result.update(status='phrase_failed',error=str(exc));return result
    result['shared_intent']=intent
    for variant,phrase in zip(result['variants'],phrases):
        variant['phrase']=phrase
    for variant in result['variants']:
        phrase=variant['phrase'];n=variant['target_letters']
        try:raw=await ask('carrier',carrier_prompt(request,intent,phrase),OUTPUT_TOKEN_LIMIT,n)
        except Exception as exc:
            variant.update(status='api_error',error=str(exc));result.update(status='api_error',error=str(exc));return result
        try:variant.update(carrier=validate_carrier(strict_json(raw),phrase['code']),status='completed')
        except ValueError as exc:variant.update(status='carrier_failed',error=str(exc))
    result['status']='completed' if all(v['status']=='completed' for v in result['variants']) else 'partial_failure'
    return result
