const pptxgen = require('pptxgenjs');
const { createElementMapRecorder } = require('/workspace/.plugin-cache/sha256-tree-v1-6562a7a9a9a69af61724f6f5a3cf2b2049410641553731506ce9071693edf57c/skills/pptx/scripts/mavis-ppt-map.cjs');

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'CHEN Niannian';
pres.company = 'The Hong Kong Polytechnic University';
pres.title = 'PetSafe-Greenery: A Dual-Constraint Agentic Workflow for Pet-Friendly Balcony Planting Design';
pres.subject = 'COMP5511 Artificial Intelligence Concepts';

const theme = {
  primary: '264653',
  secondary: '2A9D8F',
  accent: 'E76F51',
  light: 'E9C46A',
  bg: 'FFFFFF'
};

const outputPptx = './output/PetSafe-Greenery-presentation-static.pptx';
const elementMap = createElementMapRecorder({
  fileName: 'PetSafe-Greenery-presentation.pptx',
  filePath: outputPptx,
  layout: { name: 'LAYOUT_16x9', widthIn: 10, heightIn: 5.625 },
  expectedSlideCount: 10,
});
pres.__mavisElementMap = elementMap;

for (let i = 1; i <= 10; i++) {
  const n = String(i).padStart(2, '0');
  require('./slide-' + n + '.js').createSlide(pres, theme);
}

pres.writeFile({ fileName: outputPptx }).then(() => {
  elementMap.assertComplete({ slideCount: 10 });
  elementMap.writeFile('./output/PetSafe-Greenery-presentation.mavis-ppt-map.json');
  console.log('written: ' + outputPptx);
});
