// pbi-edge HTMLRewriter transform, reproduced verbatim from the reviewed local Worker source
// C:/Hecate-Umbra/work/witchcraft-identity-lock-20261013/candidates/pbi-edge/worker.js (65,987 B)
//   PLAYER_TAG       worker.js:193
//   convaiTag()      worker.js:199-208
//   NETWORK_DEFAULT  worker.js:139
//   LAYOUT           worker.js:616
//   footerBlock = "" worker.js:634 -- eclipse.shadow.black and eclipse.witch.best are absent from SPONSORS,
//                   SPONSORS2 and ORIGIN_LEGAL_HOSTS, so no legal block is injected
//   agentFor()       worker.js:150-153 -- absent from AGENTS, so NETWORK_DEFAULT is used.
//
// The live pages carry agent_7601kv76b5cgfq9thvb5mxsdqsw0, which IS NETWORK_DEFAULT.id: proof that no
// AGENTS entry matched for this host, which is itself proof of the routing path.
//
// NOTE the trailing-newline question: measured on this estate, the HTMLRewriter payload
// lands FLUSH against </body> when footerBlock is "" (no trailing newline). Re-derive it
// per site; do not carry this belief forward unverified.

export const PLAYER_TAG = '<script src="/_pbi/player.js" defer></script>';

// NOTE: both style blocks end in TWO closing braces - one closes the element selector,
// one closes the @media rule. Generate these as literal assignments, never through
// str.format(), which consumes one brace from each and silently costs 2 bytes.
export const LAYOUT =
  "<style>elevenlabs-convai{right:16px!important;bottom:24px!important}" +
  "@media(max-width:640px){elevenlabs-convai{right:10px!important;bottom:76px!important}}</style>";

export const NETWORK_DEFAULT = {
  id: "agent_7601kv76b5cgfq9thvb5mxsdqsw0",
  c1: "#c9c5bb",
  c2: "#0a0a0a",
};

export function convaiTag(a) {
  return (
    "<style>elevenlabs-convai{position:fixed;right:16px;bottom:24px;z-index:2147482000}" +
    "@media(max-width:640px){elevenlabs-convai{bottom:76px;right:10px}}</style>" +
    '<elevenlabs-convai agent-id="' + a.id +
    '" avatar-orb-color-1="' + a.c1 + '" avatar-orb-color-2="' + a.c2 +
    '"></elevenlabs-convai>' +
    '<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>'
  );
}
