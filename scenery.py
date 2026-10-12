"""Card styles for Last Light: beige paper, sage green accents. Pure string, no network."""

CSS = """
:root{--beige:#f3ecdc;--paper:rgba(247,242,230,.9);--sage:#9caf88;--sage-deep:#4f6b50;--ink:#2b3328;--soft:#5d6657;--rule:#b9b49f}
html{background:var(--beige)}
body{margin:0;min-height:100vh;color:var(--ink);font:1.08rem/1.6 "Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif}
.scene{position:fixed;top:0;right:0;bottom:0;left:0;z-index:0;background-size:cover;background-position:center}
.paper{position:relative;z-index:1;max-width:33rem;margin:2.5rem auto;padding:1.6rem 1.6rem 2rem;background:var(--paper);border:1px solid var(--sage);border-radius:6px}
h1{font-size:1.75rem;line-height:1.2;margin:0 0 .6rem;color:var(--sage-deep)}
h2{font-size:1.1rem;margin:1.7rem 0 .3rem;color:var(--sage-deep)}
.times{border-top:2px solid var(--sage);border-bottom:2px solid var(--sage);padding:.6rem 0;margin:1rem 0}
.times p{margin:.15rem 0}
ul{padding-left:1.2rem;margin:.3rem 0}
code{font-size:.9em}
.lines div{border-bottom:1px solid var(--rule);height:2rem}
.trophy svg{width:10rem;height:auto;display:block;margin-top:1.5rem}
.src{color:var(--soft);font-size:.85rem;margin-top:2rem}
@media (max-width:34rem){.paper{margin:0;border-radius:0;border-left:0;border-right:0}}
@media print{.scene{opacity:.25}.paper{background:none;border:0;margin:0;padding:0}}
"""
