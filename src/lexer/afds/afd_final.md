graph LR
  subgraph Legend
    L0["[A] letras A..Z,a..z"]:::legend
    L1["[D] dígitos 0..9"]:::legend
    L2["[WS] espaço, \\t, \\f, \\r"]:::legend
    L3["[NL] \\n"]:::legend
    L4["[IDc] letras/dígitos/_"]:::legend
    classDef legend fill:#eee,stroke:#999,color:#333;
  end

  q0((q0)) -->|"[WS]"| q0
  q0 -->|"[NL]"| q0
  q0 -->|'""'| qS("String…"):::acc
  q0 -->|"/"| qSlash
  q0 -->|"."| qDot
  q0 -->|"[A] or _"| qId(((ID)))
  q0 -->|"[D]"| qNum(((Num)))
  q0 -->|ops| qOp(((Op)))

  %% Comentários
  qSlash -->|'""'| qLC("LINE_COMMENT"):::acc
  qSlash -->|"/"| qLC2("LINE_COMMENT2"):::acc

  %% IDs
  qId -->|"[IDc]"| qId
  qId:::acc

  %% Números
  qNum -->|"."| qFloat
  qNum -->|"[D]"| qNum
  qFloat -->|"[D]"| qFloat
  qFloat -->|"e/E (+/-)? [D]+"| qExp
  qExp:::acc
  qFloat:::acc
  qNum:::acc

  %% Strings (fechamento abreviado)
  qS -->|"conteúdo/escape"| qS
  qS -->|'""'| qS_end:::acc

  %% Pontos
  qDot -->|"."| qDot2
  qDot2 -->|"."| qDot3:::acc
  qDot2:::acc
  qDot:::acc

  %% Operadores/delims
  qOp:::acc

  classDef acc fill:#bbf,stroke:#333,color:#000,stroke-width:2px;