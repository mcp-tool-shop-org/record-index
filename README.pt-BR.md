<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# índice de registros

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

Um mapa SQLite+FTS5 governado sobre um registro de decisão em formato Markdown, para que uma sessão possa **consultar** o registro em vez de lê-lo — e, em seguida, ler as quarenta linhas às quais a consulta se refere, em vez das seiscentas que teria lido superficialmente.

**[Página inicial e manual →](https://mcp-tool-shop-org.github.io/record-index/)**

O Markdown permanece no formato original. O índice é derivado, regenerado a cada iteração, controlado por um conjunto de quatro `verify`, e **está incorreto por definição no dia em que é editado manualmente**.

## Status — extraído, testado, ainda não disponível no PyPI

*(Esta seção dizia "APENAS ESTRUTURA — nenhum código de ferramenta está neste repositório ainda" até 11 de agosto de 2026, o que foi falsificado pela página inicial da extração. Corrigido no local.)*

**A extração foi concluída.** O pacote está em `main`, controlado durante a inclusão por identidade de bytes com a versão do facet no repositório (19/19) e **zero diferenças no nível da linha** no mesmo corpus. Duas aplicações são executadas nele: [facet](https://github.com/mcp-tool-shop-org/facet), cujas ~2.462 linhas no repositório se tornaram uma declaração mais um adaptador com ~140 de seus testes, exercitando o pacote através dele, e [armature](https://github.com/mcp-tool-shop-org/armature), cujo próprio índice foi inicializado com 15/15 e 47 regras.

**O pacote contém sua própria suíte: 455 verificações** em todos os dez módulos, executadas em CI no Python 3.11 e 3.13, construídas sobre dois repositórios de registros que divergem em todos os eixos declaráveis — marcadores, raízes do corpus, regras de arco, vocabulário de verificação, formatos de cabeçalho — para que uma implementação incorreta tenha algum lugar onde possa se tornar visível. **Dependências: nenhuma.** Apenas a biblioteca padrão (`sqlite3` + `re` + `json`), e essa é uma propriedade declarada, não um acidente.

**Quatro defeitos são conhecidos, reproduzidos e fixados no repositório como testes `xfail(strict=True)`**, em vez de ocultos: `verify()` dobra suas contagens de diagnóstico (as etapas de controle permanecem inalteradas); o padrão claim-arc assume arcos numerados com `E`; o localizador de sub-regras não é derivado do formato de cabeçalho declarado; e quatro campos de declaração não podem ser declarados como vazios. Nenhum afeta as duas aplicações atuais; todos os quatro estão na fila para a próxima versão.

**Ainda não disponível no PyPI.** `release.yml` publica via OIDC Trusted Publishing quando uma nova versão é criada no GitHub; nada é publicado ao fazer um push.

## De onde isso vem

Esta é uma extração do índice de registros construído e aprimorado em [`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet), que é onde todas as convenções abaixo foram pagas. Ele extrai em vez de criar um fork porque o próprio livro de regras do facet registra cinco cópias manuais de uma função, vivendo sob quatro nomes, invisíveis a uma pesquisa baseada em nome por meses; criar um fork de milhares de linhas em um segundo repositório é esse erro com mais três zeros.

A condição de extração foi declarada antecipadamente e controlada por meio de medição: *o índice é extraído quando um segundo repositório adota as convenções.* [`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) é esse repositório.

## O design, em um parágrafo

Um repositório de registros declara **o que seus documentos significam** — quais arquivos contêm regras, quais formatos de cabeçalho os abrem, qual é o seu vocabulário de verificação e quais corpora ele possui. A ferramenta fornece **como a pesquisa funciona** — análise sintática, classificação, determinismo, as etapas de verificação — com valores de ajuste que carregam o corpus e a data em que foram calibrados. As convenções são uma **declaração completa** (um repositório declara seu próprio significado; ele nunca herda o histórico de outro repositório por omissão). O mecanismo é **valores padrão com substituições**.

Cada vocabulário relata o que **não reconheceu**. Uma tabela vazia e uma tabela que descartou silenciosamente seis artefatos são indistinguíveis no local da chamada, e apenas uma delas está correta.

## A interrupção que costumava estar aqui e como ela terminou

*(Até 11 de agosto de 2026, esta seção interrompia a construção em caso de colisão medida. A interrupção era real, a regra foi definida e a construção prosseguiu — mantida aqui como o registro, em vez de excluída.)*

A etapa de classificação havia medido que derivar o arco de um documento de seu prefixo `E\d\d` **causa uma colisão em 7 chaves primárias** em relação ao facet (`E10-ruling.md` e `E10-offsurface-ruling.md` se tornam ambos o arco `E10`). O executor detectou isso em relação a um teste cujo nome registra o mesmo erro, a regra conjunta foi retirada e rederivada, e a extração prosseguiu através de seus portões. O registro — evidências, as respostas revogadas e a regra que as substituiu — está em `armature/docs/dispatches/` (o arco S02).

## Licença

MIT — veja [LICENSE](LICENSE).
