#!/usr/bin/env python3
"""Produce a complete pt-BR rendition of README.md without dropping paragraphs.

Network translation is a first pass; key passages have authorial/contextual
Portuguese renderings, and all source structural positions are retained.
This script is an explicit editorial tool, not a change to the original README.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
import threading
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "README.md"
PT = ROOT / "README-ptBR.md"
SRC = EN.read_text(encoding="utf-8")
LINES = SRC.splitlines()
BASE = "https://translate.googleapis.com/translate_a/single"
TIMEOUT = 25
CONCURRENCY = 3
TRANSLATION_LOCK = threading.Lock()
CACHED = {}

# The title, character names and specific pieces of creative work remain
# unchanged; the surrounding context is translated into Brazilian Portuguese.
PROTECTED = [
    "RAW REASONING", "Anne Marie François", "Anne Marie Grothendiek",
    "Alexander Grothendieck", "Antonio Battaglia", "Bruno Daygorô",
    "Grothendieck", "Grothendiek", "Winston", "Julia", "Dulcineia",
    "Camille", "Gérard", "Daygorô", "Marabunta", "Cambrian Radiation Computing",
    "Cambrian Radiation", "Niccolò", "Panopticon", "Killer Tech",
    "D.I.E.", "Piano di Sorrento", "Quartieri Spagnoli", "Cicciolina",
    "Galactus", "Silver Surfer", "Quixote", "Sancho",
    "Príncipe Messias", "Bob Marley & The Wailers", "Bob Marley",
    "Rosa Negra", "Björk", "Bauhaus", "Soundgarden", "Sepultura",
    "Dead Kennedys", "Red Hot Chili Peppers", "Elvis Presley",
    "Johnny Cash", "Ministry", "Jake Blues", "Blues Brothers",
    "Blood Sugar Sex Magik", "Natural Mystic", "Papéis e Papéis",
    "Ratamahatta", "Rusty Cage", "Enter Sandman", "Fado Mutante",
    "Everybody Needs Somebody to Love", "Could You Be Loved",
    "A Little Less Conversation", "Thieves", "California Über Alles",
    "All Is Full of Love", "Terror Couple Kill Colonel", "Punky Reggae Party",
    "Little Crazy", "Iris", "Cop Killer", "Self Killer",
    "Mouth for War", "One Good Man", "O mio babbino caro", "Ne me quitte pas",
    "Amazing Grace", "We Are Family", "Ape and Essence", "Lone Wolf and Cub",
    "The Incredible and Sad Tale of Innocent Eréndira and Her Heartless Grandmother",
    "Terminator 2", "The Prince", "Nineteen Eighty-Four",
    "Dodge Viper", "Ferrari F40",
    "“Ela sou eu! Temos que salvá-la!”", "“Próximo!”",
    "“Resolvo seu problema em cinco minutos.”",
    "“Eu quero ser criança, mãe. Desculpa.”",
    "“fazer aquilo de novo.”", "“Fui eu.”",
    "DONE", "DOING", "TODO",
]
PROTECTED.sort(key=len, reverse=True)

# Full-line editorial translations: exact story meaning is paramount.
# Matched by a distinctive source prefix; other lines go through the
# ordinary paragraph-preserving translation path.
MANUAL = {
    "## **DOING** — An animated audiovisual opera":
        "## **DOING** — Uma ópera audiovisual de animação — uma obra de ficção original, uma história de amor e uma visão de mundo",
    "**[View the PDF dossier](README.pdf)**":
        "**[Veja o dossiê em PDF](README-ptBR.pdf)**",
    "**Creative concept dossier |":
        "**Dossiê de concepção criativa | Material de trabalho | Edição de apresentação em português brasileiro | Desenvolvimento narrativo ampliado**",
    "> **An original work of fiction.**":
        "> **Uma obra de ficção original.** Criada a partir de referências culturais, experiências vividas e relatos de outras pessoas. Seus personagens, relações, conflitos e acontecimentos são construções ficcionais, não representações de pessoas reais identificáveis.",
    "**Editorial frame.**":
        "**Enquadramento editorial.** *RAW REASONING* é **ficção original**, formada por referências culturais, observações da vida e histórias ouvidas ao longo do tempo. Nenhum personagem ou acontecimento dramático deste dossiê deve ser apresentado como biografia de uma pessoa particular identificável, declaração dirigida a uma pessoa real identificável ou afirmação sobre descendentes reais de uma figura histórica. As relações familiares descritas abaixo são **relações entre personagens fictícios**. Confia-se na capacidade do público de interpretar significados sem aulas expositivas de medicina, moral, sociologia ou religião.",
    "**Name and origin.**":
        "**Nome e origem.** **Anne Marie François** é da **Guiana Francesa**, *não de Paramaribo, no Suriname*. O nome **Grothendiek**, usado anteriormente, é um nome ou uma identidade ficcional relacionada a Grothendieck, cujo uso preciso ao lado de François ainda precisa ser definido; não se deve tratá-lo silenciosamente como sobrenome de nascimento. O vínculo de paternidade com o matemático histórico Alexander Grothendieck é uma **invenção ficcional deliberada, não uma afirmação biográfica**. A cidade de origem na Guiana Francesa, a cronologia completa do primeiro encontro do casal e revelações anteriores relacionadas a Paramaribo ainda precisam ser conciliadas. **Outras cenas explicitamente ambientadas em Paramaribo não mudam de lugar automaticamente.**",
    "She is a **Rastafarian":
        "Ela é **rastafári, com uma vivência profundamente religiosa de matriz israelita/bíblica**. Sua devoção corporal e seu estudo são **atividades religiosas autênticas para a personagem**, jamais imitação vazia do judaísmo ou adereço visual exótico. Seu balanço lento e pesaroso evoca a oração e o estudo junto ao Muro Ocidental; os dreadlocks podem produzir um eco visual intencional dos cachos laterais usados por alguns judeus ortodoxos. São correspondências deliberadas na direção da cena, não uma afirmação de que todos os rastafáris e judeus têm classificações ou práticas religiosas idênticas. A direção de câmera deve respeitar a sinceridade de sua devoção.",
    "**Musical movement I — Príncipe Messias.**":
        "**Movimento musical I — Príncipe Messias.** A cena começa no registro doloroso de **“Papéis e Papéis”**, de **Príncipe Messias**. Entre suas tensões temáticas estão os sábios autoproclamados, os poetas de rua, os livros e o pensamento, e a luta para enfrentar o terror com coragem e amor. Na passagem que fala de poetas de rua chorando sobre o livro dos pensamentos, Anne Marie se move **lentamente, com tristeza e de maneira ritualística**, num balanço que recorda a oração e a expressividade corporal de **Bob Marley**, mas inicialmente marcado pelo luto. Ela imagina seu pai, **Alexander Grothendieck**, dançando devagar e tristemente ao som da música e sofre intensamente ao recordar o sofrimento dele. **As cinzas do pai integram o significado memorial da cena**, mas *onde elas estão guardadas* ainda não foi definido e não deve ser inventado. O movimento é um ato espiritual sincero e um lamento íntimo, não coreografia decorativa.",
    "**Musical movement II — the discovery.**":
        "**Movimento musical II — a descoberta.** Num parágrafo ou numa página de Grothendieck, ela encontra **uma razão**: a ideia tem força matemática e talvez existencial; a proposição e seu significado exatos ainda estão abertos. **“Papéis e Papéis” se funde gradualmente com “Natural Mystic”, de Bob Marley & The Wailers**. São agora **duas referências musicais sucessivas e entrelaçadas**, não músicas concorrentes entre as quais se deve escolher. À medida que chegam a compreensão e a euforia, Anne Marie começa a dançar **exatamente como Bob Marley** — referência de interpretação deliberadamente reconhecível, não um balanço genérico parecido com reggae. A tristeza não é apagada: sua expressão corporal se transforma, do lamento à alegria arrebatadora de compreender.",
    "**Lyrics and complete localization.**":
        "**Letras e localização integral.** As palavras das músicas integram a imagem como **tipografia distribuída espacialmente por todo o quadro**, não apenas como legendas convencionais no rodapé. Cada versão linguística deve traduzir/localizar o texto exibido e animar sua posição em relação à imagem e ao ritmo. Usar somente letras autorizadas para a produção; estas notas descrevem a colocação dramática, sem reproduzir longos trechos de letras protegidas. As sobreposições exatas das faixas, os cortes e a sincronização audiovisual ainda dependerão do trabalho com as gravações.",
    "**“Próximo!”**":
        "**“Próximo!”** Depois da intensa experiência pessoal, Anne Marie anuncia calmamente: **“Próximo!”** A câmera revela uma fila razoavelmente longa de pessoas com notebooks, cadernos, livros escolares e exercícios. **“Resolvo seu problema em cinco minutos.”** É assim que ela ganha dinheiro: matemática, tarefas escolares, problemas técnicos e visitantes com demandas intelectuais variadas. Ela adapta o idioma e a velocidade da fala a cada cliente. A revelação não é uma piada nem um discurso explicativo sobre sua genialidade.",
    "**Treatment and a character's choice.**":
        "**Tratamento e uma decisão da personagem.** Anne Marie toma **quetiapina, lítio e ácido valproico**. No dia da bebida, decide **não tomar sua medicação**, acreditando que assim reduzirá uma possível interação. A escolha é **um fato da personagem**, não recomendação clínica, e não explica automaticamente sua genialidade, religião, velocidade da fala, personalidade ou criatividade. O filme não a diagnostica por meio de uma montagem de traços nem diz ao espectador o que concluir. **A saúde mental é um tema dramático recorrente, tanto no longa quanto nos outros episódios**, tratado por meio de pessoas e ações particulares, não de uma palestra.",
    "**The lovers' earlier dilemma.**":
        "**O dilema anterior dos amantes.** Antonio teme ter filhos que possam herdar **seu transtorno bipolar**, percebido por ele como uma maldição que não suporta transmitir. Anne Marie revela que **ela também é bipolar**. Para Antonio, isso **agrava o problema, em vez de resolvê-lo**. Mesmo assim, escolhem a intimidade sexual: a decisão **não** decorre do desaparecimento do perigo nem de uma refutação científica do receio. Reúne desejo, autonomia, medo e uma escolha trágica cujo significado emocional poderá voltar quando os filhos se voltarem uns contra os outros. O filme não equipara automaticamente a decisão de fazer sexo à decisão de conceber; o vínculo exato entre elas pertence ao roteiro.",
    "**Fundamental architecture of intelligence in the fiction":
        "**Arquitetura fundamental da inteligência nesta ficção (6 de novembro de 2026).** **Winston e Julia, os robôs corporificados, têm inteligência acima da média humana, mas inteiramente dentro dos parâmetros cognitivos humanos.** **Não são mentes extraordinárias, sobre-humanas ou hiperinteligentes** só por serem artificiais ou terem corpos de aparência extraordinária. Sua vida emocional, seus erros de raciocínio, seu autoengano, seu amor e sua responsabilidade moral devem ser compreensíveis como os de **mentes situadas na faixa humana**.",
    "**The truly hyperintelligent entities are the AIs":
        "**As entidades realmente hiperinteligentes são as IAs executadas nos datacenters de GPUs.** Sua capacidade intelectual está categoricamente além da de Winston e Julia. **O acesso remoto pode ampliar temporariamente as capacidades dos robôs com ferramentas ou orientação desses sistemas, mas não torna hiperinteligente sua própria inteligência nativa, incorporada.** Ter uma interface com uma inteligência muito superior e *ser* essa inteligência são coisas diferentes. Não confundir concepção corporal, sensores perceptivos (inclusive o zoom dos olhos de Julia), velocidade de execução, precisão, potência computacional externa conectada e inteligência.",
    "**Consequences for the wedding/disconnection.**":
        "**Consequências para o casamento e a desconexão.** Quando Winston e Julia destroem deliberadamente suas interfaces de rede, **perdem o apoio e o acesso às IAs dos datacenters**, inclusive eventuais extensões cognitivas conectadas, **mas continuam sendo indivíduos com inteligência acima da média, dentro da faixa humana**, em seus corpos. Não se deve retratar a hiperinteligência do datacenter como inerente aos corpos deles, nem afirmar que a desconexão os transforma de superinteligências em inteligências humanas. A identidade exata e as relações técnicas entre os agentes corporificados e as IAs remotas, e quais capacidades ou lembranças subsistem depois, ainda precisam ser resolvidas; essa distinção é definitiva.",
    "**Julia remains Julia.**":
        "**Julia continua sendo Julia.** Ela **pede a Winston que a chame de “Dulcineia”**; é **uma forma íntima de tratamento, não uma mudança de nome legal ou permanente**. Winston **não entende o motivo** desse pedido. A alusão a Cervantes pode estar disponível ao espectador sem que a cena explique os motivos de Julia. Preservar a assimetria de conhecimento; não inventar um monólogo explicativo nem presumir que um conhece toda a vida interior do outro.",
    "Two embodied artificial beings, **Winston and Julia**":
        "Dois seres artificiais corporificados, **Winston e Julia**, desenvolvem uma relação cortês: metade camaradagem, metade rivalidade elegante. **Sua inteligência é acima da média humana, mas inteiramente dentro dos limites humanos; as IAs verdadeiramente hiperinteligentes operam em datacenters de GPUs, não nos corpos dos robôs.** A infraestrutura anterior e suas conexões remotas são distintas daquilo que conseguem pensar e sentir localmente. **Nenhum dos dois se chama Galactus ou Silver Surfer.** A IA masculina deve **evocar** Galactus para o público; a feminina, o Silver Surfer. São ressonâncias visuais e arquetípicas distantes, não afirmações de que sejam personagens da Marvel.",
    "### **DOING** — From the far-right rally":
        "### **DOING** — Do comício da extrema direita ao soul, à alegria coletiva e à catástrofe",
    "**Firm narrative sequence.**":
        "**Sequência narrativa definida.** Um **protesto antifascista** enfrenta um **comício político da extrema direita**. Inicialmente predomina a paisagem sonora industrial e agressiva do **Ministry**. Um **manifestante toma o palco e o microfone do comício**. Em vez de fazer um discurso político, começa o **curto monólogo introdutório de “Everybody Needs Somebody to Love”**, interpretando-o **como Jake Blues em *The Blues Brothers***. A fala abre caminho para a canção, substituindo a atmosfera musical áspera. A gravação exata do Ministry ainda não foi escolhida definitivamente: **“Thieves”** era uma candidata anterior, e **“California Über Alles”, dos Dead Kennedys**, uma alternativa mais antiga. A **progressão agora estabelecida** é Ministry → introdução falada à maneira dos Blues Brothers → *Everybody Needs Somebody to Love*.",
    "**The neighborhood enters the music.**":
        "**A vizinhança entra na música.** **Os robôs começam a se abraçar** e a dançar. A festa se espalha. **Moradores que antes estavam escondidos, com medo da manifestação, começam a sair às ruas**. **Aviõezinhos de papel são lançados das janelas; sanduíches são jogados das janelas para alimentar os manifestantes**. O espaço passa do medo e do confronto à alegria e à hospitalidade compartilhadas, por meio da ação e da música, não de falas explicativas. Ideias improvisadas anteriormente sobre moradores específicos, um policial dividindo comida ou outros passos de dança não foram, por isso, aprovadas como fatos do roteiro.",
    "**The rupture.**":
        "**A ruptura.** Ao fim da sequência jubilosa vem o **silêncio absoluto**: sem desaceleração confortável, transição explicativa ou aviso. **Atrás das linhas policiais**, **Julia amplia a imagem com seus olhos artificiais** e observa um policial junto a uma jovem indefesa ou inconsciente. Julia acredita, equivocadamente, que ele tenta cometer uma violência sexual. **Na realidade, o policial está tentando salvar a mulher.** O grito de Julia — **“Ela sou eu! Temos que salvá-la!”** — expressa **empatia e identificação**, não confusão quanto à identidade da jovem.",
    "**Winston intervenes and kills.**":
        "**Winston intervém e mata.** Winston age porque **acredita que uma desconhecida inocente precisa ser salva**. Ele **sabe que a mulher não é Julia**. Imaginar que **Julia poderia estar naquela situação** reforça seu sentimento, mas **não é a motivação principal da tentativa de resgate**. No terrível equívoco, **Winston mata o policial inocente**. O fato de o policial estar socorrendo a mulher só fica claro posteriormente; não se deve oferecer ao espectador um amortecedor explicativo antecipado. O assassinato é **um ato de Winston**, não um crime conjunto indistinto atribuído igualmente às duas IAs. A interpretação equivocada de Julia é essencial à cadeia causal.",
    "**Evidence and aftermath.**":
        "**Provas e consequências.** Mais tarde, **gravações de múltiplos ângulos** revelam o que o policial realmente fazia. Winston aceita as provas e se arrepende profundamente; Julia tem muito mais dificuldade para aceitá-las. O musical de rua precedente mostrou a capacidade das IAs de amar e ser solidárias; a morte repentina impede que essas qualidades sejam confundidas com infalibilidade. O corte é deliberadamente tão abrupto que o público **não tem nem tempo de “pegar pipoca”** entre a euforia coletiva e a atrocidade. O tempo exato, os ângulos de câmera e a coreografia do confronto ainda serão desenvolvidos. Os direitos das gravações e do monólogo falado exigiriam autorização ou alternativas originais; nenhum trecho do monólogo protegido é reproduzido aqui.",
    "**Winston believes he is rescuing an innocent woman**":
        "**Winston acredita estar salvando uma mulher inocente**. A ideia de que ela *poderia ter sido Julia* intensifica a emoção, mas **não condiciona a compaixão dele à semelhança da vítima com Julia**. **Winston mata o policial inocente** antes que o público compreenda plenamente a situação. O policial tentava salvar a mulher, não machucá-la. É **Winston quem mata**; o erro de interpretação de Julia e a intenção compartilhada de ajudar continuam relevantes, mas não fazem dela a autora material do assassinato.",
    "**The policeman is innocent.**":
        "**O policial é inocente.** Ele está socorrendo a manifestante inconsciente. **Julia interpreta equivocadamente sua observação visual ampliada como uma tentativa iminente de violência sexual**. Winston age para defender uma vítima desconhecida, emocionalmente mobilizado também pela possibilidade de sua companheira estar numa situação parecida, e **mata o policial**. Seus corpos são protótipos fisicamente frágeis, não máquinas de combate sobre-humanas. O **silêncio após o musical coletivo** e a rapidez do erro irreversível fazem parte do choque audiovisual pretendido.",
    "**Before their network access is removed**":
        "**Antes de perderem o acesso à rede**, quando ainda podem consultar **IAs hiperinteligentes nos datacenters de GPUs** e outras ferramentas remotas, Winston e Julia examinam gravações completas de múltiplos ângulos. **O raciocínio próprio de seus corpos permanece acima da média, mas dentro da faixa humana** o tempo todo. As evidências demonstram a inocência do policial. Winston é tomado pelo remorso. Julia, diante do colapso de sua autoimagem virtuosa e de seu grito **“Ela sou eu! Temos que salvá-la!”**, recusa-se a acreditar no que as gravações mostram. A divergência é epistemológica e psicológica: ambos têm acesso às **mesmas provas**, mas não conseguem suportá-las da mesma maneira. A negação dela não deve ser validada pelo filme.",
    "She asks **him to destroy her communicator to the network**":
        "Ela pede **a Winston que destrua seu comunicador de rede**: não suporta o conhecimento que a condena. Ele concorda. Depois, **Winston pede que Julia destrua o comunicador dele**, pois não suporta a memória plenamente vívida de ter matado um inocente. Ele não nega as provas; quer escapar da permanência delas. Um rompe a conexão do outro com **sistemas de IA hiperinteligentes em datacenters de GPUs**. Assim, perdem acesso a uma **inteligência externa** extraordinariamente poderosa, sem descartar uma suposta superinteligência nativa instalada nos corpos. **Sua capacidade cognitiva própria continua humana**. Trocam **votos de casamento** enquanto fazem isso: uma perda recíproca e voluntária de capacidade externa, ao mesmo tempo declaração de confiança e pacto de evasão.",
    "**RAW REASONING: All Rights Reserved.**":
        "**RAW REASONING: Todos os direitos reservados.** Este conceito, os personagens, a arte e a narrativa ficcional podem ser lidos, discutidos e divulgados por meio de links públicos, mas não se concede permissão geral para reproduzir, redistribuir, adaptar, explorar comercialmente, treinar IA com o material ou reivindicar sua autoria. Os repositórios reais de software vinculados aqui têm licenças próprias; essas licenças não se aplicam a esta animação.",
    "**Music policy (DOING):**":
        "**Política musical (EM ELABORAÇÃO):** A intenção principal continua sendo uma trilha composta originalmente, mas gravações comerciais específicas estão sendo consideradas como referências para cenas, especialmente *A Little Less Conversation*, de Elvis Presley; *Blood Sugar Sex Magik*, dos Red Hot Chili Peppers; *Rusty Cage*, do Soundgarden; as alternativas propostas para a manifestação; e *Little Crazy*, do Fight. **Nenhuma dessas gravações está licenciada.** A utilização definitiva exige as autorizações cabíveis sobre composição e gravação original, ou sua substituição por música original.",
    "*The cover is a deliberately layered pitch illustration":
        "*A capa é uma ilustração conceitual deliberadamente composta de várias camadas, destinada à apresentação para leitores criativos e possíveis colaboradores. Ela **não é um quadro do filme acabado**; suas referências recorrentes não correspondem necessariamente a informações que o público verá na tela.*",
    "*Cover concept: Anne Marie comforting Antonio":
        "*Conceito da capa: Anne Marie amparando Antonio; Camille e Daygorô; Winston e Julia, os dois amantes robóticos, em roupas contemporâneas de rebeldia urbana; e um volume bastante manuseado de Grothendieck. Os emblemas, as bandeiras da Itália e da Jamaica e as referências matemáticas recorrentes são pistas intencionais de ancestralidade, criadores humanos e identidade escolhida. A tipografia matemática e a edição retratada do livro pertencem à ilustração conceitual, não a um fac-símile verificado.*",
    "*RAW REASONING* is a proposed animated audiovisual work":
        "*RAW REASONING* é um projeto de obra audiovisual animada de aproximadamente 100 minutos, concebido como uma ópera não linear composta de videoclipes narrativos, passagens dramáticas, interlúdios, cenas próximas do recitativo, rimas visuais e silêncio. A obra pode passar de figuras de palitos deliberadamente rudimentares e comédia familiar desbocada a interpretações de intensa intimidade psicológica e a uma única sequência de refinamento visual quase obsessivo.",
    "## **DOING** — Consolidated character, opening":
        "## **DOING** — Decisões consolidadas sobre personagens, abertura e tramas paralelas (6 de novembro de 2026)",
    "At a busy railway station, Anne Marie sells books":
        "Numa estação ferroviária movimentada, Anne Marie vende livros e artesanato matematicamente elaborado; entre os volumes oferecidos está *A Incrível e Triste História de Cândida Erêndira e Sua Avó Desalmada*, de Gabriel García Márquez. Seu estimado livro de Grothendieck **não está à venda**. Ela não está simplesmente lendo: sua relação com o texto reúne matemática, luto e **ritual religioso**.",
    "**Late afternoon and departure plan.**":
        "**Fim da tarde e plano de mudança.** Já no fim da tarde, **um garoto lhe traz uma bebida** (a bebida exata e a relação entre os dois ainda não foram definidas). Anne Marie costuma **tomar banho nos banheiros da estação** para economizar, juntando dinheiro para se mudar para **São Paulo**. A sequência do banho **não apresenta nudez** nem tem tratamento erótico. A precariedade material e a disciplina pessoal coexistem com suas capacidades extraordinárias.",
    "The formerly **unnamed male and female embodied AIs**":
        "Os dois seres artificiais corporificados, antes **sem nomes definidos**, passam a se chamar **Winston e Julia**, numa referência deliberada aos amantes de *1984*, de George Orwell. Os nomes evocam amor, autonomia corporal e a ameaça de controle sobre a vida interior. Eles não são os personagens de Orwell nem reproduzem seu enredo ou suas posições morais: respondem por suas próprias escolhas.",
    "Interwoven with their story is a human drama:":
        "Entrelaçado à história dos robôs, há um drama humano: **Anne Marie François**, uma andarilha e prodígio matemático oriunda da Guiana Francesa, com uma ligação ficcional deliberada com Alexander Grothendieck; **Antonio**, engenheiro de software e consultor falível; e sua família — **Camille**, **Gérard** e **Daygorô**. Suas vidas imperfeitas têm importância numa escala cósmica. Perto do final, uma música de Bob Marley acompanha uma montagem de coragem, brincadeira, constrangimento e reconciliação humanos. Na coda familiar, Anne Marie revela uma capacidade matemática muito superior à de Camille e Gérard e então conta a Antonio que é a garota de quem ele se lembra da Guiana Francesa. O breve espanto dele se transforma numa perseguição brincalhona; os irmãos discutem por uma aposta de cinquenta reais. As duas escalas — a cósmica e a teimosamente cotidiana — nunca se separam completamente. As invenções fictícias de Antonio se conectam a **repositórios técnicos reais e experimentais da Cambrian Radiation**, vinculados mais adiante, enquanto a história imagina resultados ainda não alcançados na realidade.",
    "Daygorô joins in, taking his mother's martial world absolutely seriously.":
        "Daygorô entra na cena levando o universo marcial da mãe absolutamente a sério. Imita o aquecimento dela e golpeia um pedaço de madeira com a convicção desproporcional de uma criança pequena brincando de guerreiro. As demonstrações de Camille são muitíssimo mais poderosas; impacto, madeira se partindo e sangue cartunesco extravagante empurram a cena para o exagero. Gérard aparece, avalia a combinação de mãe e filho e, prudentemente, recua. Seus comentários e a conversa sobre uma aposta envolvendo Camille revelam o afeto familiar sob a aparente carnificina.",
}

def replace_fixed_terms(text: str) -> tuple[str, dict[str, str]]:
    markers = {}
    def stash(value: str) -> str:
        key = "QZX" + f"{len(markers):04d}" + "XZQ"
        markers[key] = value
        return key
    # Preserve markdown links and code spans as full units. URLs stay valid.
    reserved = r"(\[[^\]\n]+\]\([^\)\n]+\)|" + chr(96) + r"[^" + chr(96) + r"]*" + chr(96) + r"|https?://[^\s)]+)"
    text = re.sub(reserved, lambda m: stash(m.group(0)), text)
    for name in PROTECTED:
        text = text.replace(name, stash(name)) if name in text else text
    return text, markers

def normalize_markers(text: str, markers: dict[str,str]) -> str:
    # Translation systems can insert a space inside an opaque marker.
    for key, value in markers.items():
        marker_pattern = re.escape(key)
        marker_pattern = marker_pattern.replace("QZX", r"QZX\s*").replace("XZQ", r"\s*XZQ")
        text = re.sub(marker_pattern, lambda m: value, text, flags=re.I)
    return text

def google(text: str) -> str:
    if not text.strip():
        return text
    with TRANSLATION_LOCK:
        if text in CACHED:
            return CACHED[text]
    for attempt in range(9):
        try:
            response = requests.get(BASE, params={
                "client": "gtx", "sl": "en", "tl": "pt", "dt": "t", "q": text,
            }, timeout=TIMEOUT, headers={"User-Agent":"Mozilla/5.0"})
            if response.status_code in (429, 503):
                raise RuntimeError(f"Translate HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            translated = "".join(part[0] for part in payload[0] if part and part[0] is not None)
            if not translated.strip():
                raise ValueError("Translation returned empty text")
            with TRANSLATION_LOCK:
                CACHED[text] = translated
            return translated
        except Exception as exc:
            if attempt == 8:
                raise RuntimeError(f"Could not translate {text[:80]!r}: {exc}") from exc
            time.sleep(min(2 ** attempt, 25))
    raise RuntimeError("unreachable")

def translate_line(line: str) -> str:
    if not line.strip():
        return line
    if line.strip() == "---" or line.startswith("# RAW REASONING"):
        return line
    for prefix, translation in MANUAL.items():
        if line.startswith(prefix):
            return translation
    # Keep markdown block structure, and translate the prose of each line.
    match = re.match(r"^(\s*(?:#{1,6}\s+|[-*+] (?=\S)|\d+\. (?=\S)|>\s*))", line)
    prefix = match.group(0) if match else ""
    body = line[len(prefix):]
    if not body or body.startswith("|---"):
        return line
    if len(body) > 4000:
        raise ValueError("Unexpected oversized source line")
    protected, markers = replace_fixed_terms(body)
    result = google(protected)
    result = normalize_markers(result, markers)
    if re.search(r"QZX\s*\d{4}\s*XZQ", result, flags=re.I):
        raise RuntimeError("Unrestored translation placeholder: "+result[:80])
    # Preserve literal emphasis/markup marker counts (repeat without translating
    # markdown delimiters when formatting got damaged).
    if body.count("**") != result.count("**"):
        # Google sometimes moves star separators; use authorial source markers
        # instead of allowing malformed Markdown silently.
        alt_body, alt_markers = replace_fixed_terms(body.replace("**"," QZXBOLDXZQ "))
        alt = normalize_markers(google(alt_body), alt_markers)
        result = re.sub(r"\s*QZXBOLDXZQ\s*", "**", alt)
        if result.count("**") != body.count("**"):
            # Rebuild only this line from independently translated plain/strong
            # spans. This trades a little local context for certain valid markup.
            chunks = re.split(r"(\\*\\*.*?\\*\\*)", body)
            recovered = []
            for chunk in chunks:
                if not chunk:
                    continue
                strong = chunk.startswith("**") and chunk.endswith("**")
                content = chunk[2:-2] if strong else chunk
                safe_text, safe_markers = replace_fixed_terms(content)
                value = normalize_markers(google(safe_text), safe_markers)
                # Any stray star markers in a plain span can be discarded.
                if not strong:
                    value = value.replace("**", "")
                recovered.append("**" + value + "**" if strong else value)
            result = "".join(recovered)
            if result.count("**") != body.count("**"):
                raise RuntimeError("Bold formatting could not be reconstructed in "+body[:80])
            print("Rebuilt strong spans for:", body[:65], flush=True)
    return prefix + result

def main() -> None:
    result: list[str | None] = [None] * len(LINES)
    indexes = [i for i, line in enumerate(LINES) if line.strip()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        tasks = {pool.submit(translate_line, LINES[i]): i for i in indexes}
        done = 0
        for future in concurrent.futures.as_completed(tasks):
            i = tasks[future]
            result[i] = future.result()
            done += 1
            if done % 35 == 0:
                print(f"Translated {done}/{len(indexes)} content lines", flush=True)
    for i, line in enumerate(LINES):
        if result[i] is None:
            result[i] = line

    document = "\n".join(result) + "\n"
    for source_label, target_label in [
        ("**DONE**", "**DEFINIDO**"),
        ("**DOING**", "**EM ELABORAÇÃO**"),
        ("**TODO**", "**PENDENTE**"),
    ]:
        document = document.replace(source_label, target_label)

    # Native pt-BR editorial corrections: grammatical gender, soundtrack idiom,
    # existing Portuguese dialogue, and official/common cultural titles.
    editorial_replacements = [
        ("**Política musical (DOING):**", "**Política musical (EM ELABORAÇÃO):**"),
        ("**Música DOING:**", "**Música em elaboração:**"),
        ("**Cronologia/edição DOING:**", "**Cronologia e montagem em elaboração:**"),
        ("*Nineteen Eighty-Four*", "*1984*"),
        ("*The Prince*", "*O Príncipe*"),
        ("*Ape and Essence*", "*O Macaco e a Essência*"),
        ("*The Incredible and Sad Tale of Innocent Eréndira and Her Heartless Grandmother*", "*A Incrível e Triste História de Cândida Erêndira e Sua Avó Desalmada*"),
        ("**Winston tenta salvar o estranho**", "**Winston tenta salvar a desconhecida**"),
        ("com o estranho ameaçado", "com a desconhecida ameaçada"),
        ("com o estranho vulnerável", "com a desconhecida vulnerável"),
        ("a estranho vulnerável", "a desconhecida vulnerável"),
        ("**Um tipo diferente de assassinato.**", "**Uma outra forma de matar.**"),
        ("**O policial é inocente.**", "**O policial é inocente.**"),
        ("E que ele vai embora com sua culpa eterna.", "E que ele vá embora com sua culpa eterna."),
        ("no brilho imediato", "no instante imediatamente posterior ao amor"),
        ("o brilho imediato", "o instante imediatamente posterior ao amor"),
        ("seu brilho imediato", "o instante imediatamente posterior ao amor"),
        ("o seu brilho imediato", "o instante imediatamente posterior ao amor"),
        ("a sua", "sua"),
        ("As demonstrações do Camille", "As demonstrações de Camille"),
        ("Daygorô se junta a nós", "Daygorô entra na cena"),
        ("A sequência do banho **sem nudez**", "A sequência do banho **não apresenta nudez**"),
        ("Nenhum dos dois foi esclarecido.", "Nenhuma das duas gravações foi licenciada."),
        ("a IA masculina sem nome", "Winston"),
        ("a IA feminina sem nome", "Julia"),
        ("uma IA masculina sem nome", "Winston"),
        ("uma IA feminina sem nome", "Julia"),
        ("personagem do sexo feminino", "personagem feminina"),
        ("os dois amantes robóticos anônimos", "Winston e Julia, os dois amantes robóticos"),
        ("tratamento de capa imaginado", "tratamento imaginado como versão cover"),
        ("tratamento de capa imaginado", "releitura musical imaginada"),
        ("de um livro Grothendieck", "de um livro de Grothendieck"),
        ("O seu assassinato é uma tragédia de falsas inferências", "A morte provocada por ele é uma tragédia nascida de uma inferência equivocada"),
        ("uma proposta de", "uma proposta de"),
        ("uma casa de hóspedes amarela", "uma pousada amarela"),
        ("regista", "registra"),
        ("exactas", "exatas"),
        ("exacto", "exato"),
        ("exacta", "exata"),
    ]
    for a, b in editorial_replacements:
        document = document.replace(a, b)

    # Apply linked-PDF naming even in translator-produced prose.
    document = document.replace("(README.pdf)", "(README-ptBR.pdf)")
    # After machine coverage, apply reviewed literary/contextual lines from
    # exact matching English paragraphs. Their meaning and punctuation survive
    # any future re-run of this translation tool.
    overrides_file = ROOT / "scripts" / "ptBR_editorial_overrides.json"
    if overrides_file.exists():
        translated_lines = document.splitlines()
        items = json.loads(overrides_file.read_text("utf-8"))["overrides"]
        for item in items:
            source_line = item["source_line"]
            matches = [j for j, value in enumerate(LINES) if value == source_line]
            if len(matches) != 1:
                raise RuntimeError("Editorial override source missing or ambiguous: " + source_line[:90])
            translated_lines[matches[0]] = item["pt_line"]
        document = "\n".join(translated_lines) + "\n"
    expected = sum(1 for s in LINES if re.match(r"^#{1,4} ", s))
    actual = sum(1 for s in document.splitlines() if re.match(r"^#{1,4} ", s))
    if expected != actual:
        raise RuntimeError(f"Missing heading(s): English={expected}, Portuguese={actual}")
    if len(document.splitlines()) != len(LINES):
        raise RuntimeError("Paragraph/line preservation mismatch")
    if len(document) < len(SRC) * 0.62:
        raise RuntimeError("Suspiciously incomplete translated content")
    for token in [
        "RAW REASONING", "Winston", "Julia", "Dulcineia", "Grothendieck",
        "Ministry", "Blues Brothers", "Guiana Francesa", "quetiapina",
        "sanduíches", "datacenters de GPUs", "Winston mata o policial",
        "(README-ptBR.pdf)",
    ]:
        if token not in document:
            raise RuntimeError("Missing crucial dramatic element: " + token)
    if "QZX" in document:
        leftovers = re.findall(r"QZX\S{0,50}", document)
        raise RuntimeError("Unrestored translator placeholder: "+str(leftovers[:4]))
    PT.write_text(document, encoding="utf-8")
    print(f"SUCCESS: {PT.name}: {len(document)} chars; {actual} headings; {len(LINES)} lines", flush=True)

if __name__ == "__main__":
    main()
