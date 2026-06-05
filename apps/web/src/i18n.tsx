import { createContext, useContext, useState, type ReactNode } from 'react'

// The 5 World Cup languages Granite narrates in. The narration was already 5-language;
// this lifts the SAME language choice up to a context so the whole PAGE chrome flips with
// it (hero, problem, demo, pipeline, judges, footer), not just the spoken verdict.
// The canonical language list + order, single source of truth (the picker, the 1-5 keyboard
// cycle, and the Lang union all derive from this so adding a language is a one-line change).
export const LANGS = ['English', 'Spanish', 'French', 'Portuguese', 'German'] as const
export type Lang = (typeof LANGS)[number]

export type Chrome = {
  heroKicker: string
  skipToContent: string
  tagline: string
  ctaHear: string
  ctaWhy: string
  scroll: string
  problemEyebrow: string
  problemH2: string
  problemIntro: string
  cards: { h: string; p: string }[]
  demoEyebrow: string
  demoH2: string
  demoIntro: string
  pipelineEyebrow: string
  pipelineH2: string
  pipelineIntro: string
  pipeline: { k: string; d: string }[]
  judgesEyebrow: string
  judgesH2: string
  judgesIntro: string
  runHeading: string
  runHelper: string
  footerH2: string
  footerP: string
  footerWC: string
}

export const CHROME: Record<Lang, Chrome> = {
  English: {
    heroKicker: 'IFAB-grounded · screen-reader-native',
    skipToContent: 'Skip to the demo',
    tagline: 'Hear the why behind every VAR call.',
    ctaHear: 'Hear it explain a call',
    ctaWhy: 'Why it matters',
    scroll: 'scroll',
    problemEyebrow: 'The problem',
    problemH2: 'The last to know',
    problemIntro:
      'When a VAR review stops the match, a blind fan is often the last person in the room to understand the call. The decision data exists. It just never reaches them in real time.',
    cards: [
      {
        h: 'The moment',
        p: 'The stadium goes quiet. Everyone stares at the big screen. You wait for someone to explain what just happened.',
      },
      {
        h: 'What fans told us',
        p: 'A blind supporter who follows the A-League told us the TV commentary leaves him with no idea what is happening on the pitch.',
      },
      {
        h: 'The gap',
        p: 'Audio description is improving, but even great commentary rarely gives the rule-grounded reason behind a contested call.',
      },
    ],
    demoEyebrow: 'Live',
    demoH2: 'Hear the call',
    demoIntro:
      'A real 2022 World Cup offside, explained end to end. Press play and listen, or cut the network and run it on your own device.',
    pipelineEyebrow: 'Under the hood',
    pipelineH2: 'One event, fanned out',
    pipelineIntro:
      'Four backends coordinate through the IBM Context Forge gateway with Granite on top. One VAR event fans out across the services and returns a single, safe, rule-grounded answer. The live gateway recorded those tool calls at 100% success.',
    pipeline: [
      { k: 'Trigger', d: 'A VAR review fires (live feed or a StatsBomb 360 frame).' },
      { k: 'Geometry', d: 'The real offside margin in meters, from the freeze-frame.' },
      { k: 'IFAB Law', d: 'The governing Law of the Game, retrieved from the corpus.' },
      { k: 'IBM Granite', d: 'A plain explanation, coordinated through Context Forge.' },
      { k: 'Guardian', d: 'Granite Guardian checks it stays grounded in the Law.' },
      { k: 'Screen reader', d: 'Spoken in your language through your own screen reader.' },
    ],
    judgesEyebrow: 'For judges',
    judgesH2: 'Every claim is verifiable',
    judgesIntro:
      'No theater. Each capability below runs in this repository and is pointed at the exact file that proves it. Built on IBM Granite, Granite Guardian, Context Forge, and Docling.',
    runHeading: 'Run it now, against the live backend',
    runHelper:
      'These buttons call the deployed API from your browser and show the real response. The free backend can cold-start on the first call (about 30 seconds).',
    footerH2: 'For the fan who needs it most.',
    footerP:
      'VARSITY turns officials-only decision data into the first rule-grounded, accessible why. It complements the commentary you love, it does not replace it.',
    footerWC: 'World Cup 2026',
  },
  Spanish: {
    heroKicker: 'Basado en las Reglas IFAB · nativo para lectores de pantalla',
    skipToContent: 'Saltar a la demostración',
    tagline: 'Escucha el porqué de cada decisión del VAR.',
    ctaHear: 'Escucha cómo explica una jugada',
    ctaWhy: 'Por qué importa',
    scroll: 'desplázate',
    problemEyebrow: 'El problema',
    problemH2: 'El último en enterarse',
    problemIntro:
      'Cuando una revisión del VAR detiene el partido, un aficionado ciego suele ser el último en entender la decisión. Los datos existen. Simplemente nunca le llegan en tiempo real.',
    cards: [
      {
        h: 'El momento',
        p: 'El estadio se queda en silencio. Todos miran la pantalla gigante. Tú esperas a que alguien te explique qué acaba de pasar.',
      },
      {
        h: 'Lo que nos dijeron los aficionados',
        p: 'Un aficionado ciego que sigue la A-League nos dijo que los comentarios de la televisión lo dejan sin idea de lo que pasa en el campo.',
      },
      {
        h: 'La brecha',
        p: 'La audiodescripción mejora, pero ni el mejor relato suele dar la razón, basada en las reglas, detrás de una decisión polémica.',
      },
    ],
    demoEyebrow: 'En vivo',
    demoH2: 'Escucha la jugada',
    demoIntro:
      'Un fuera de juego real del Mundial 2022, explicado de principio a fin. Pulsa reproducir y escucha, o corta la red y ejecútalo en tu propio dispositivo.',
    pipelineEyebrow: 'Por dentro',
    pipelineH2: 'Un evento, distribuido',
    pipelineIntro:
      'Cuatro servicios se coordinan a través de la puerta de enlace IBM Context Forge, con Granite por encima. Un evento del VAR se distribuye entre los servicios y devuelve una única respuesta segura y basada en las reglas. La puerta de enlace registró esas llamadas con un 100% de éxito.',
    pipeline: [
      { k: 'Disparo', d: 'Se activa una revisión del VAR (señal en vivo o un fotograma de StatsBomb 360).' },
      { k: 'Geometría', d: 'El margen real de fuera de juego en metros, a partir del fotograma.' },
      { k: 'Regla IFAB', d: 'La Regla de Juego aplicable, recuperada del corpus.' },
      { k: 'IBM Granite', d: 'Una explicación clara, coordinada a través de Context Forge.' },
      { k: 'Guardian', d: 'Granite Guardian comprueba que se mantiene fiel a la Regla.' },
      { k: 'Lector de pantalla', d: 'Narrado en tu idioma a través de tu propio lector de pantalla.' },
    ],
    judgesEyebrow: 'Para el jurado',
    judgesH2: 'Cada afirmación es verificable',
    judgesIntro:
      'Sin teatro. Cada capacidad de abajo se ejecuta en este repositorio y apunta al archivo exacto que la demuestra. Construido sobre IBM Granite, Granite Guardian, Context Forge y Docling.',
    runHeading: 'Ejecútalo ahora, contra el backend en vivo',
    runHelper:
      'Estos botones llaman a la API desplegada desde tu navegador y muestran la respuesta real. El backend gratuito puede tardar en arrancar en la primera llamada (unos 30 segundos).',
    footerH2: 'Para el aficionado que más lo necesita.',
    footerP:
      'VARSITY convierte los datos de decisión, antes solo para árbitros, en el primer porqué accesible y basado en las reglas. Complementa el relato que amas, no lo reemplaza.',
    footerWC: 'Mundial 2026',
  },
  French: {
    heroKicker: "Fondé sur les Lois de l'IFAB · pensé pour les lecteurs d'écran",
    skipToContent: 'Aller à la démo',
    tagline: 'Entendez le pourquoi de chaque décision de la VAR.',
    ctaHear: "Écoutez-le expliquer une action",
    ctaWhy: "Pourquoi c'est important",
    scroll: 'défiler',
    problemEyebrow: 'Le problème',
    problemH2: 'Le dernier au courant',
    problemIntro:
      "Quand un contrôle de la VAR arrête le match, un supporter aveugle est souvent le dernier à comprendre la décision. Les données existent. Elles ne lui parviennent simplement jamais en temps réel.",
    cards: [
      {
        h: "L'instant",
        p: "Le stade se tait. Tout le monde fixe l'écran géant. Vous attendez que quelqu'un vous explique ce qui vient de se passer.",
      },
      {
        h: 'Ce que les supporters nous ont dit',
        p: "Un supporter aveugle qui suit la A-League nous a dit que les commentaires télé le laissent sans savoir ce qui se passe sur le terrain.",
      },
      {
        h: 'Le manque',
        p: "L'audiodescription s'améliore, mais même un bon commentaire donne rarement la raison, fondée sur les règles, derrière une décision contestée.",
      },
    ],
    demoEyebrow: 'En direct',
    demoH2: "Écoutez l'action",
    demoIntro:
      "Un vrai hors-jeu de la Coupe du monde 2022, expliqué de bout en bout. Lancez la lecture et écoutez, ou coupez le réseau et exécutez-le sur votre appareil.",
    pipelineEyebrow: 'Sous le capot',
    pipelineH2: 'Un événement, déployé',
    pipelineIntro:
      "Quatre services se coordonnent via la passerelle IBM Context Forge, avec Granite au-dessus. Un événement de la VAR se déploie sur les services et renvoie une seule réponse sûre et fondée sur les règles. La passerelle a enregistré ces appels avec 100% de réussite.",
    pipeline: [
      { k: 'Déclenchement', d: "Un contrôle de la VAR se déclenche (flux en direct ou une image StatsBomb 360)." },
      { k: 'Géométrie', d: "La marge réelle de hors-jeu en mètres, à partir de l'image figée." },
      { k: 'Loi IFAB', d: 'La Loi du Jeu applicable, extraite du corpus.' },
      { k: 'IBM Granite', d: 'Une explication claire, coordonnée via Context Forge.' },
      { k: 'Guardian', d: "Granite Guardian vérifie qu'elle reste fidèle à la Loi." },
      { k: "Lecteur d'écran", d: "Énoncé dans votre langue par votre propre lecteur d'écran." },
    ],
    judgesEyebrow: 'Pour le jury',
    judgesH2: 'Chaque affirmation est vérifiable',
    judgesIntro:
      "Pas de mise en scène. Chaque capacité ci-dessous s'exécute dans ce dépôt et pointe vers le fichier exact qui la prouve. Bâti sur IBM Granite, Granite Guardian, Context Forge et Docling.",
    runHeading: "Lancez-le maintenant, sur le backend en direct",
    runHelper:
      "Ces boutons appellent l'API déployée depuis votre navigateur et affichent la vraie réponse. Le backend gratuit peut démarrer à froid au premier appel (environ 30 secondes).",
    footerH2: "Pour le supporter qui en a le plus besoin.",
    footerP:
      "VARSITY transforme les données de décision, réservées aux arbitres, en le premier pourquoi accessible et fondé sur les règles. Il complète le commentaire que vous aimez, il ne le remplace pas.",
    footerWC: 'Coupe du monde 2026',
  },
  Portuguese: {
    heroKicker: 'Baseado nas Regras da IFAB · nativo para leitores de tela',
    skipToContent: 'Ir para a demonstração',
    tagline: 'Ouça o porquê de cada decisão do VAR.',
    ctaHear: 'Ouça como explica um lance',
    ctaWhy: 'Por que importa',
    scroll: 'rolar',
    problemEyebrow: 'O problema',
    problemH2: 'O último a saber',
    problemIntro:
      'Quando uma revisão do VAR para a partida, um torcedor cego costuma ser o último a entender a decisão. Os dados existem. Só que nunca chegam a ele em tempo real.',
    cards: [
      {
        h: 'O momento',
        p: 'O estádio fica em silêncio. Todos olham para o telão. Você espera que alguém explique o que acabou de acontecer.',
      },
      {
        h: 'O que os torcedores nos disseram',
        p: 'Um torcedor cego que acompanha a A-League nos disse que a narração da TV o deixa sem ideia do que acontece no campo.',
      },
      {
        h: 'A lacuna',
        p: 'A audiodescrição está melhorando, mas mesmo uma boa narração raramente dá o motivo, baseado nas regras, por trás de uma decisão polêmica.',
      },
    ],
    demoEyebrow: 'Ao vivo',
    demoH2: 'Ouça o lance',
    demoIntro:
      'Um impedimento real da Copa do Mundo de 2022, explicado do início ao fim. Toque em reproduzir e ouça, ou corte a rede e execute no seu próprio dispositivo.',
    pipelineEyebrow: 'Por dentro',
    pipelineH2: 'Um evento, distribuído',
    pipelineIntro:
      'Quatro serviços se coordenam pelo gateway IBM Context Forge, com o Granite no topo. Um evento do VAR se distribui pelos serviços e retorna uma única resposta segura e baseada nas regras. O gateway registrou essas chamadas com 100% de sucesso.',
    pipeline: [
      { k: 'Gatilho', d: 'Uma revisão do VAR é acionada (sinal ao vivo ou um quadro do StatsBomb 360).' },
      { k: 'Geometria', d: 'A margem real de impedimento em metros, a partir do quadro.' },
      { k: 'Regra IFAB', d: 'A Regra do Jogo aplicável, recuperada do corpus.' },
      { k: 'IBM Granite', d: 'Uma explicação clara, coordenada pelo Context Forge.' },
      { k: 'Guardian', d: 'O Granite Guardian verifica que ela continua fiel à Regra.' },
      { k: 'Leitor de tela', d: 'Falado no seu idioma pelo seu próprio leitor de tela.' },
    ],
    judgesEyebrow: 'Para os jurados',
    judgesH2: 'Cada afirmação é verificável',
    judgesIntro:
      'Sem teatro. Cada recurso abaixo é executado neste repositório e aponta para o arquivo exato que o comprova. Construído sobre IBM Granite, Granite Guardian, Context Forge e Docling.',
    runHeading: 'Execute agora, no backend ao vivo',
    runHelper:
      'Estes botões chamam a API implantada do seu navegador e mostram a resposta real. O backend gratuito pode demorar a iniciar na primeira chamada (cerca de 30 segundos).',
    footerH2: 'Para o torcedor que mais precisa.',
    footerP:
      'A VARSITY transforma os dados de decisão, antes só dos árbitros, no primeiro porquê acessível e baseado nas regras. Complementa a narração que você ama, não a substitui.',
    footerWC: 'Copa do Mundo 2026',
  },
  German: {
    heroKicker: 'Auf IFAB-Regeln gestützt · für Screenreader gemacht',
    skipToContent: 'Zur Demo springen',
    tagline: 'Hören Sie das Warum hinter jeder VAR-Entscheidung.',
    ctaHear: 'Hören Sie die Erklärung einer Szene',
    ctaWhy: 'Warum es zählt',
    scroll: 'scrollen',
    problemEyebrow: 'Das Problem',
    problemH2: 'Die Letzten, die es erfahren',
    problemIntro:
      'Wenn eine VAR-Überprüfung das Spiel stoppt, ist ein blinder Fan oft der Letzte, der die Entscheidung versteht. Die Daten existieren. Sie erreichen ihn nur nie in Echtzeit.',
    cards: [
      {
        h: 'Der Moment',
        p: 'Das Stadion wird still. Alle starren auf die Leinwand. Sie warten, dass jemand erklärt, was gerade passiert ist.',
      },
      {
        h: 'Was Fans uns sagten',
        p: 'Ein blinder Anhänger der A-League sagte uns, die TV-Kommentare ließen ihn im Unklaren darüber, was auf dem Spielfeld geschieht.',
      },
      {
        h: 'Die Lücke',
        p: 'Audiodeskription wird besser, aber selbst guter Kommentar nennt selten den regelbasierten Grund hinter einer strittigen Entscheidung.',
      },
    ],
    demoEyebrow: 'Live',
    demoH2: 'Hören Sie die Szene',
    demoIntro:
      'Ein echtes Abseits der WM 2022, von Anfang bis Ende erklärt. Starten Sie die Wiedergabe und hören Sie zu, oder trennen Sie das Netz und führen Sie es auf Ihrem Gerät aus.',
    pipelineEyebrow: 'Hinter den Kulissen',
    pipelineH2: 'Ein Ereignis, verteilt',
    pipelineIntro:
      'Vier Dienste koordinieren sich über das IBM-Context-Forge-Gateway, mit Granite darüber. Ein VAR-Ereignis verteilt sich über die Dienste und liefert eine einzige sichere, regelbasierte Antwort. Das Gateway protokollierte diese Aufrufe mit 100% Erfolg.',
    pipeline: [
      { k: 'Auslöser', d: 'Eine VAR-Überprüfung wird ausgelöst (Live-Signal oder ein StatsBomb-360-Bild).' },
      { k: 'Geometrie', d: 'Der reale Abseitsabstand in Metern, aus dem Standbild.' },
      { k: 'IFAB-Regel', d: 'Die geltende Spielregel, aus dem Korpus abgerufen.' },
      { k: 'IBM Granite', d: 'Eine klare Erklärung, koordiniert über Context Forge.' },
      { k: 'Guardian', d: 'Granite Guardian prüft, dass sie der Regel treu bleibt.' },
      { k: 'Screenreader', d: 'In Ihrer Sprache über Ihren eigenen Screenreader gesprochen.' },
    ],
    judgesEyebrow: 'Für die Jury',
    judgesH2: 'Jede Aussage ist überprüfbar',
    judgesIntro:
      'Kein Theater. Jede Fähigkeit unten läuft in diesem Repository und verweist auf die genaue Datei, die sie belegt. Gebaut auf IBM Granite, Granite Guardian, Context Forge und Docling.',
    runHeading: 'Jetzt ausführen, gegen das Live-Backend',
    runHelper:
      'Diese Schaltflächen rufen die bereitgestellte API aus Ihrem Browser auf und zeigen die echte Antwort. Das kostenlose Backend kann beim ersten Aufruf kalt starten (etwa 30 Sekunden).',
    footerH2: 'Für den Fan, der es am meisten braucht.',
    footerP:
      'VARSITY verwandelt die bisher nur den Offiziellen vorbehaltenen Entscheidungsdaten in das erste regelbasierte, barrierefreie Warum. Es ergänzt den Kommentar, den Sie lieben, es ersetzt ihn nicht.',
    footerWC: 'WM 2026',
  },
}

const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({
  lang: 'English',
  setLang: () => {},
})

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>('English')
  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>
}

export function useLang() {
  return useContext(LangContext)
}
