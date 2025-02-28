"""Block to fix case-enhanced dependency relations in Russian."""
from udapi.core.block import Block
import logging
import re

class FixEdeprels(Block):

    # Sometimes there are multiple layers of case marking and only the outermost
    # layer should be reflected in the relation. For example, the semblative 'как'
    # is used with the same case (preposition + morphology) as the nominal that
    # is being compared ('как_в:loc' etc.) We do not want to multiply the relations
    # by all the inner cases.
    # The list in the value contains exceptions that should be left intact.
    outermost = {
        'более_чем':  [],
        'будто':      [],
        'ведь':       [],
        'если':       [],
        'как':        ['как_только'],
        'когда':      [],
        'нежели':     [],
        'плюс':       [],
        'потому_что': [],
        'пусть':      [],
        'раз':        [],
        'словно':     [],
        'так_что':    [],
        'хоть':       [],
        'хотя':       [],
        'чем':        [],
        'что':        []
    }

    # Secondary prepositions sometimes have the lemma of the original part of
    # speech. We want the grammaticalized form instead. List even those that
    # will have the same lexical form, as we also want to check the morphological
    # case. And include all other prepositions that have unambiguous morphological
    # case, even if they are not secondary.
    unambiguous = {
        'loc':              'в:loc',
        'в_вид':            'в_виде:gen',
        'в_качество':       'в_качестве:gen',
        'в_отношение':      'в_отношении:gen',
        'в_связь_с':        'в_связи_с:ins',
        'в_случай_если':    'в_случае_если',
        'в_соответствие_с': 'в_соответствии_с:ins',
        'в_течение':        'в_течение:gen',
        'в_тот_время_как':  'в_то_время_как',
        'в_ход':            'в_ходе:gen',
        'вблизи':           'вблизи:gen',
        'вместо':           'вместо:gen',
        'во_глава':         'во_главе_с:ins',
        'во_глава_с':       'во_главе_с:ins',
        'во_избежание':     'во_избежание:gen',
        'возле':            'возле:gen',
        'вокруг':           'вокруг:gen',
        'вплоть_до':        'вплоть_до:gen',
        'вроде':            'вроде:gen',
        'выше':             'выше:gen',
        'для':              'для:gen',
        'до':               'до:gen',
        'до_то_как':        'до:gen', # до того, как ...
        'за_исключение':    'за_исключением:gen',
        'из':               'из:gen',
        'к':                'к:dat',
        'ко':               'ко:dat',
        'кроме':            'кроме:gen',
        'над':              'над:ins', # at least I have not encountered any genuine example of accusative
        'несмотря_на':      'несмотря_на:acc',
        'ниже':             'ниже:gen',
        'около':            'около:gen',
        'от':               'от:gen',
        'относительно':     'относительно:gen',
        'по_мера':          'по_мере:gen',
        'по_мера_то_как':   'по_мере_того_как',
        'по_отношение_ко?': 'по_отношению_к:dat',
        'по_повод':         'по_поводу:gen',
        'по_сравнение_с':   'по_сравнению_с:ins',
        'помимо':           'помимо:gen',
        'порядка':          'порядка:gen',
        'после':            'после:gen',
        'при':              'при:loc',
        'при_помощь':       'при_помощи:gen',
        'при_условие_что':  'при_условии_что',
        'про':              'про:acc',
        'против':           'против:gen',
        'с_помощь':         'с_помощью:gen',
        'с_тот_пора_как':   'с_тех_пор_как',
        'свыше':            'свыше:gen',
        'со_сторона':       'со_стороны:gen',
        'согласно':         'согласно:dat',
        'спустя':           'спустя:acc',
        'у':                'у:gen',
        'через':            'через:acc',
        'чтоб':             'чтобы'
    }

    def copy_case_from_adposition(self, node, adposition):
        """
        In some treebanks, adpositions have the Case feature and it denotes the
        valency case that the preposition's nominal must be in.
        """
        # The following is only partial solution. We will not see
        # some children because they may be shared children of coordination.
        prepchildren = [x for x in node.children if x.lemma == adposition]
        if len(prepchildren) > 0 and prepchildren[0].feats['Case'] != '':
            return adposition+':'+prepchildren[0].feats['Case'].lower()
        else:
            return None

    def process_node(self, node):
        """
        Occasionally the edeprels automatically derived from the Russian basic
        trees do not match the whitelist. For example, the noun is an
        abbreviation and its morphological case is unknown.
        """
        for edep in node.deps:
            m = re.match(r'^(obl(?::arg)?|nmod|advcl|acl(?::relcl)?):', edep['deprel'])
            if m:
                bdeprel = m.group(1)
                solved = False
                # If the marker is 'быть', discard it. It represents the phrase 'то есть', which should not be analyzed as introducing a subordinate clause.
                edep['deprel'] = re.sub(r':(быть|столько).*', '', edep['deprel'])
                # Some markers should be discarded only if they occur as clause markers (acl, advcl).
                edep['deprel'] = re.sub(r'^(advcl|acl(?::relcl)?):(в|вместо|при)$', r'\1', edep['deprel'])
                # If the case marker starts with 'столько', remove this part.
                # It occurs in the expressions of the type 'сколько...столько' but the real case marker of the modifier is something else.
                # Similarly, 'то' occurs in 'то...то' and should be removed.
                edep['deprel'] = re.sub(r':(столько|то|точно)[_:]', ':', edep['deprel'])
                # If one of the following expressions occurs followed by another preposition
                # or by morphological case, remove the additional case marking. For example,
                # 'словно_у' becomes just 'словно'.
                for x in self.outermost:
                    exceptions = self.outermost[x]
                    m = re.match(r'^(obl(?::arg)?|nmod|advcl|acl(?::relcl)?):'+x+r'([_:].+)?$', edep['deprel'])
                    if m and m.group(2) and not x+m.group(2) in exceptions:
                        edep['deprel'] = m.group(1)+':'+x
                        solved = True
                        break
                if solved:
                    continue
                for x in self.unambiguous:
                    # All secondary prepositions have only one fixed morphological case
                    # they appear with, so we can replace whatever case we encounter with the correct one.
                    m = re.match(r'^(obl(?::arg)?|nmod|advcl|acl(?::relcl)?):'+x+r'(?::(?:nom|gen|dat|acc|voc|loc|ins))?$', edep['deprel'])
                    if m:
                        edep['deprel'] = m.group(1)+':'+self.unambiguous[x]
                        solved = True
                        break
                if solved:
                    continue
                # The following prepositions have more than one morphological case
                # available. Thanks to the Case feature on prepositions, we can
                # identify the correct one.
                # Both "на" and "в" also occur with genitive. However, this
                # is only because there are numerals in the phrase ("в 9 случаев из 10")
                # and the whole phrase should not be analyzed as genitive.
                m = re.match(r'^(obl(?::arg)?|nmod):(в|во|на|о)(?::(?:nom|gen|dat|voc|ins))?$', edep['deprel'])
                if m:
                    adpcase = self.copy_case_from_adposition(node, m.group(2))
                    if adpcase:
                        edep['deprel'] = m.group(1)+':'+adpcase
                    else:
                        # Accusative or locative are possible. Pick locative.
                        edep['deprel'] = m.group(1)+':'+m.group(2)+':loc'
                    continue
                # Unlike in Czech, 'над' seems to allow only instrumental and not accusative.
                m = re.match(r'^(obl(?::arg)?|nmod):(за|под)(?::(?:nom|gen|dat|voc|loc))?$', edep['deprel'])
                if m:
                    adpcase = self.copy_case_from_adposition(node, m.group(2))
                    if adpcase:
                        edep['deprel'] = m.group(1)+':'+adpcase
                    else:
                        # Accusative or instrumental are possible. Pick accusative.
                        edep['deprel'] = m.group(1)+':'+m.group(2)+':acc'
                    continue
                m = re.match(r'^(obl(?::arg)?|nmod):(между)(?::(?:nom|dat|acc|voc|loc))?$', edep['deprel'])
                if m:
                    adpcase = self.copy_case_from_adposition(node, m.group(2))
                    if adpcase:
                        edep['deprel'] = m.group(1)+':'+adpcase
                    else:
                        # Genitive or instrumental are possible. Pick genitive.
                        edep['deprel'] = m.group(1)+':'+m.group(2)+':gen'
                    continue
                m = re.match(r'^(obl(?::arg)?|nmod):(по)(?::(?:nom|gen|voc|ins))?$', edep['deprel'])
                if m:
                    adpcase = self.copy_case_from_adposition(node, m.group(2))
                    if adpcase:
                        edep['deprel'] = m.group(1)+':'+adpcase
                    else:
                        # Dative, accusative or locative are possible. Pick dative.
                        edep['deprel'] = m.group(1)+':'+m.group(2)+':dat'
                    continue
                m = re.match(r'^(obl(?::arg)?|nmod):(с)(?::(?:nom|dat|acc|voc|loc))?$', edep['deprel'])
                if m:
                    adpcase = self.copy_case_from_adposition(node, m.group(2))
                    if adpcase:
                        edep['deprel'] = m.group(1)+':'+adpcase
                    else:
                        # Genitive or instrumental are possible. Pick instrumental.
                        edep['deprel'] = m.group(1)+':'+m.group(2)+':ins'
                    continue
            if re.match(r'^(nmod|obl):', edep['deprel']):
                if edep['deprel'] == 'nmod:loc' and node.parent.feats['Case'] == 'Loc' or edep['deprel'] == 'nmod:voc' and node.parent.feats['Case'] == 'Voc':
                    # This is a same-case noun-noun modifier, which just happens to be in the locative.
                    # For example, 'v Ostravě-Porubě', 'Porubě' is attached to 'Ostravě', 'Ostravě' has
                    # nmod:v:loc, which is OK, but for 'Porubě' the case does not say anything significant.
                    edep['deprel'] = 'nmod'
                elif edep['deprel'] == 'nmod:loc':
                    edep['deprel'] = 'nmod:nom'
                elif edep['deprel'] == 'nmod:voc':
                    edep['deprel'] = 'nmod:nom'

    def set_basic_and_enhanced(self, node, parent, deprel, edeprel):
        '''
        Modifies the incoming relation of a node both in the basic tree and in
        the enhanced graph. If the node does not yet depend in the enhanced
        graph on the current basic parent, the new relation will be added without
        removing any old one. If the node already depends multiple times on the
        current basic parent in the enhanced graph, all such enhanced relations
        will be removed before adding the new one.
        '''
        old_parent = node.parent
        node.parent = parent
        node.deprel = deprel
        node.deps = [x for x in node.deps if x['parent'] != old_parent]
        new_edep = {}
        new_edep['parent'] = parent
        new_edep['deprel'] = edeprel
        node.deps.append(new_edep)
