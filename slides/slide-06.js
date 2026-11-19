const path = require('path');
const NOTES = require('./notes');
const { addMappedText, addMappedShape, addMappedImage } = require('/workspace/.plugin-cache/sha256-tree-v1-6562a7a9a9a69af61724f6f5a3cf2b2049410641553731506ce9071693edf57c/skills/pptx/scripts/mavis-ppt-map.cjs');

const FIG = path.join(__dirname, '..', 'figures');
const GOLD = 'E9C46A';
const SAND = 'F4A261';

function pageNumber(slide, map, n, theme) {
  addMappedText(slide, map, {
    elementId: 'page.number.' + n, role: 'pageNumber', text: String(n),
    x: 9.3, y: 5.08, w: 0.45, h: 0.3,
    options: { fontSize: 10, color: theme.secondary, align: 'right', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-%s.js', method: 'addText' },
  });
}

function title(slide, map, id, text, theme) {
  addMappedText(slide, map, {
    elementId: id, role: 'title', text: text,
    x: 0.55, y: 0.34, w: 8.9, h: 0.6,
    options: { fontSize: 27, bold: true, color: theme.primary, align: 'left',
               margin: 0, fontFace: 'Arial', fit: 'shrink' },
    source: { file: 'slides/slide-%s.js', method: 'addText' },
  });
}


function createSlide(pres, theme) {
  const slide = pres.addSlide();
  const map = pres.__mavisElementMap;
  map?.startSlide({ slideNumber: 6, slideId: 'evaluation', title: 'Evaluation design' });
  title(slide, map, 'evaluation.title', 'How the three methods are compared', theme);

  const methods = [
    { id: 'evaluation.method.01', tag: 'B1', name: 'Zero-shot LLM', desc: 'One prompt. The model answers from memory, with no catalogue and no filter.' },
    { id: 'evaluation.method.02', tag: 'B2', name: 'Naive keyword RAG', desc: 'Top-k retrieved species are passed to the model. Nothing is excluded.' },
    { id: 'evaluation.method.03', tag: 'P', name: 'Proposed agent', desc: 'Retrieval + negative filtering + deterministic audit with repair loops.' },
  ];
  methods.forEach((m, i) => {
    const x = 0.55 + i * 3.05;
    const isProposed = i === 2;
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: m.id + '.card', role: 'card',
      x: x, y: 1.08, w: 2.8, h: 2.1,
      options: { fill: { color: isProposed ? theme.primary : 'F6F7F6' },
                 line: { color: isProposed ? theme.primary : 'D8DEDC', width: 1 }, rectRadius: 0.06 },
      source: { file: 'slides/slide-06.js', method: 'addShape' },
    });
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: m.id + '.tag', role: 'decorative',
      x: x + 0.2, y: 1.26, w: 0.42, h: 0.3,
      options: { fill: { color: isProposed ? GOLD : theme.secondary },
                 line: { color: isProposed ? GOLD : theme.secondary, width: 0 }, rectRadius: 0.04 },
      source: { file: 'slides/slide-06.js', method: 'addShape' },
    });
    addMappedText(slide, map, {
      elementId: m.id + '.tagtext', role: 'label', text: m.tag,
      x: x + 0.2, y: 1.3, w: 0.42, h: 0.24,
      options: { fontSize: 9.5, bold: true, color: isProposed ? theme.primary : 'FFFFFF',
                 align: 'center', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-06.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: m.id + '.name', role: 'heading', text: m.name,
      x: x + 0.2, y: 1.68, w: 2.4, h: 0.38,
      options: { fontSize: 15, bold: true, color: isProposed ? 'FFFFFF' : theme.primary,
                 align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-06.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: m.id + '.desc', role: 'body', text: m.desc,
      x: x + 0.2, y: 2.1, w: 2.4, h: 0.95,
      options: { fontSize: 10.5, color: isProposed ? 'DCE8E1' : '51605A',
                 align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.1, fontFace: 'Arial' },
      source: { file: 'slides/slide-06.js', method: 'addText' },
    });
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'evaluation.fairness.card', role: 'card',
    x: 0.55, y: 3.4, w: 5.3, h: 1.55,
    options: { fill: { color: 'F1F7F4' }, line: { color: theme.secondary, width: 1 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-06.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'evaluation.fairness.heading', role: 'heading', text: 'Identical output contract for all three',
    x: 0.8, y: 3.56, w: 4.8, h: 0.32,
    options: { fontSize: 13, bold: true, color: theme.secondary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-06.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'evaluation.fairness.body', role: 'body',
    text: 'Same JSON schema, same required design content, same rubric. Only grounding and filtering differ -- so the comparison measures the architecture, not the prompt.',
    x: 0.8, y: 3.92, w: 4.8, h: 0.95,
    options: { fontSize: 11, color: theme.primary, align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.12, fontFace: 'Arial' },
    source: { file: 'slides/slide-06.js', method: 'addText' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'evaluation.metrics.card', role: 'card',
    x: 6.05, y: 3.4, w: 3.45, h: 1.55,
    options: { fill: { color: 'F6F7F6' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-06.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'evaluation.metrics.heading', role: 'heading', text: 'Five deterministic metrics',
    x: 6.3, y: 3.56, w: 2.95, h: 0.32,
    options: { fontSize: 13, bold: true, color: theme.primary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-06.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'evaluation.metrics.body', role: 'body',
    text: '1 Pet safety\n2 Horticultural viability\n3 Dual-constraint accuracy\n4 Design completeness (0-15)\n5 Out-of-database rate',
    x: 6.3, y: 3.92, w: 2.95, h: 0.95,
    options: { fontSize: 10, color: '51605A', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.08, fontFace: 'Arial' },
    source: { file: 'slides/slide-06.js', method: 'addText' },
  });
  pageNumber(slide, map, 6, theme);
  slide.addNotes(NOTES['06']);
}

module.exports = { createSlide };
