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
  map?.startSlide({ slideNumber: 4, slideId: 'method', title: 'Method' });
  title(slide, map, 'method.title', 'Method: split the task by what can be checked', theme);

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'method.figure.shell', role: 'card',
    x: 0.5, y: 1.08, w: 5.75, h: 3.85,
    options: { fill: { color: 'FFFFFF' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-04.js', method: 'addShape' },
  });
  addMappedImage(slide, map, {
    elementId: 'method.figure.image', role: 'image',
    path: path.join(FIG, 'fig_workflow.png'),
    x: 0.62, y: 1.2, w: 5.5, h: 3.6,
    source: { file: 'slides/slide-04.js', method: 'addImage' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'method.idea.card', role: 'card',
    x: 6.45, y: 1.08, w: 3.05, h: 1.28,
    options: { fill: { color: theme.primary }, line: { color: theme.primary, width: 0 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-04.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'method.idea.text', role: 'body',
    text: 'If a constraint can be checked deterministically, the LLM should not be allowed to decide it.',
    x: 6.68, y: 1.28, w: 2.6, h: 0.9,
    options: { fontSize: 12.5, bold: true, color: 'FFFFFF', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-04.js', method: 'addText' },
  });

  const steps = [
    ['1', 'Extract', 'LLM reads the brief -> pets, light class, moisture class'],
    ['2', 'Filter', 'Python removes every species toxic to a household pet'],
    ['3', 'Design', 'LLM composes zones, combination logic, care and cautions'],
    ['4', 'Audit', 'Python re-checks safety and a 15-item design rubric'],
    ['5', 'Repair', 'Violations and missing rubric items go back to the model'],
  ];
  steps.forEach((s, i) => {
    const y = 2.5 + i * 0.49;
    addMappedShape(slide, map, pres.shapes.OVAL, {
      elementId: 'method.step.' + s[0] + '.dot', role: 'decorative',
      x: 6.45, y: y, w: 0.3, h: 0.3,
      options: { fill: { color: theme.secondary }, line: { color: theme.secondary, width: 0 } },
      source: { file: 'slides/slide-04.js', method: 'addShape' },
    });
    addMappedText(slide, map, {
      elementId: 'method.step.' + s[0] + '.num', role: 'label', text: s[0],
      x: 6.45, y: y + 0.04, w: 0.3, h: 0.24,
      options: { fontSize: 10, bold: true, color: 'FFFFFF', align: 'center', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-04.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: 'method.step.' + s[0] + '.label', role: 'label', text: s[1],
      x: 6.85, y: y + 0.03, w: 0.75, h: 0.26,
      options: { fontSize: 11.5, bold: true, color: theme.primary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-04.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: 'method.step.' + s[0] + '.text', role: 'body', text: s[2],
      x: 6.85, y: y + 0.24, w: 2.65, h: 0.24,
      options: { fontSize: 9, color: '51605A', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-04.js', method: 'addText' },
    });
  });
  pageNumber(slide, map, 4, theme);
  slide.addNotes(NOTES['04']);
}

module.exports = { createSlide };
