/* Antigravity King — three.js r149 UMD, no imports or external assets. */
(function (global) {
  'use strict';
  var DEFAULT_PALETTE = Object.freeze({
    antigravityBlue: '#1686e5', silver: '#b8becd', darkGray: '#303440',
    black: '#10131a', white: '#f3f4f8', claudeRed: '#ee3946',
    gaugeYellow: '#ffd646', wingRed: '#ec3444', wingYellow: '#ffcd4b',
    wingGreen: '#168568'
  });
  var MECHANISMS = Object.freeze([
    'shinSlide', 'cowlFold', 'clawSpinOut', 'wingHinge',
    'faceplateClose', 'chestPlateFlip'
  ]);
  function bounded(value, maximum) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new TypeError('Expected a finite number');
    }
    return Math.max(0, Math.min(maximum, value));
  }
  function smooth(value) { return value * value * (3 - 2 * value); }
  function phase(value, start, end) {
    return smooth(Math.max(0, Math.min(1, (value - start) / (end - start))));
  }
  function build(overrides) {
    var THREE = global.THREE;
    if (!THREE || THREE.REVISION !== '149') {
      throw new Error('AntigravityKing requires global THREE, revision 149.');
    }
    var palette = Object.assign({}, DEFAULT_PALETTE, overrides || {});
    var root = new THREE.Group();
    root.name = 'AntigravityKing';
    var parts = { geminiJet: {}, gptShip: {}, claudeBike: {}, byName: {} };
    var geometries = new Set(), materials = new Set(), textures = new Set();
    var materialCache = {}, tracks = [], carriers = {}, cells = [], gaugeLabels = [];
    var shinJoints = [], cowlJoints = [], clawJoints = [], wingJoints = [], armJoints = [];
    var glowMaterials = [], footJoints = [], handJoints = [], meshIndex = 0, disposed = false;
    var state = { fusion: 1, scaling: 1, gauge: 1, mechanisms: {} };
    var bounds = new THREE.Box3(), scratch = new THREE.Vector3();
    var humanScale = 0.15;
    var blackColor = new THREE.Color(palette.black);
    var whiteColor = new THREE.Color(palette.white);
    var shade = blackColor.clone().lerp(whiteColor, 0.54);
    var gradient = new THREE.DataTexture(new Uint8Array([
      shade.r * 255, shade.g * 255, shade.b * 255, 255,
      whiteColor.r * 255, whiteColor.g * 255, whiteColor.b * 255, 255
    ]), 2, 1, THREE.RGBAFormat);
    gradient.minFilter = gradient.magFilter = THREE.NearestFilter;
    gradient.generateMipmaps = false;
    gradient.needsUpdate = true;
    textures.add(gradient);
    var outlineMaterial = new THREE.MeshBasicMaterial({
      color: palette.black, side: THREE.BackSide
    });
    materials.add(outlineMaterial);

    function material(key, unique) {
      if (!unique && materialCache[key]) return materialCache[key];
      var result = new THREE.MeshToonMaterial({ color: palette[key], gradientMap: gradient });
      materials.add(result);
      if (!unique) materialCache[key] = result;
      return result;
    }
    function group(path, parent) {
      var result = new THREE.Group();
      result.name = path;
      parent.add(result);
      if (path) {
        var tokens = path.split('.');
        if (tokens.length === 2 && parts[tokens[0]]) parts[tokens[0]][tokens[1]] = result;
        parts.byName[path] = result;
      }
      return result;
    }
    function surface(parent, geometry, key, position, rotation, customMaterial, outlined) {
      geometries.add(geometry);
      var result = new THREE.Mesh(geometry, customMaterial || material(key));
      result.name = parent.name + '.surface' + (++meshIndex);
      if (position) result.position.set.apply(result.position, position);
      if (rotation) result.rotation.set.apply(result.rotation, rotation);
      parent.add(result);
      if (outlined !== false) {
        var outline = new THREE.Mesh(geometry, outlineMaterial);
        outline.name = result.name + '.outline';
        geometry.computeBoundingBox();
        var center = geometry.boundingBox.getCenter(new THREE.Vector3());
        outline.scale.setScalar(1.025);
        outline.position.copy(center).multiplyScalar(-0.025);
        result.add(outline);
      }
      return result;
    }
    function box(parent, size, key, position, rotation, customMaterial, outlined) {
      return surface(parent, new THREE.BoxGeometry(size[0], size[1], size[2]),
        key, position, rotation, customMaterial, outlined);
    }
    function cylinder(parent, top, bottom, height, key, position, rotation, segments) {
      return surface(parent, new THREE.CylinderGeometry(top, bottom, height, segments || 10),
        key, position, rotation);
    }
    function polygon(parent, points, depth, key, position, rotation, customMaterial) {
      var shape = new THREE.Shape();
      points.forEach(function (point, index) {
        if (!index) shape.moveTo(point[0], point[1]);
        else shape.lineTo(point[0], point[1]);
      });
      shape.closePath();
      var geometry = new THREE.ExtrudeGeometry(shape, { depth: depth, bevelEnabled: false });
      geometry.translate(0, 0, -depth / 2);
      return surface(parent, geometry, key, position, rotation, customMaterial);
    }
    function label(parent, text, width, height, position) {
      if (!global.document) return null;
      var canvas = global.document.createElement('canvas');
      canvas.width = 512; canvas.height = 96;
      var context = canvas.getContext('2d');
      function draw(value) {
        context.fillStyle = palette.black; context.fillRect(0, 0, 512, 96);
        context.fillStyle = palette.white; context.font = 'bold 42px sans-serif';
        context.textAlign = 'center'; context.textBaseline = 'middle';
        context.fillText(value, 256, 48, 490);
      }
      draw(text);
      var texture = new THREE.CanvasTexture(canvas);
      texture.encoding = THREE.sRGBEncoding;
      textures.add(texture);
      var textMaterial = material('white', true);
      textMaterial.map = texture;
      box(parent, [width, height, 0.035], 'white', position, null, textMaterial, false);
      return { update: function (value) { draw(value); texture.needsUpdate = true; } };
    }
    function pose(position, rotation) {
      return { position: new THREE.Vector3().fromArray(position),
        quaternion: new THREE.Quaternion().setFromEuler(new THREE.Euler().fromArray(rotation || [0, 0, 0])) };
    }
    function track(part, vehiclePosition, vehicleRotation, robotPosition, robotRotation, offset) {
      var robotPose = pose(robotPosition, robotRotation);
      var spreadPosition = robotPose.position.clone().add(new THREE.Vector3().fromArray(offset || [0, 2, 0]));
      tracks.push({ part: part, vehicle: pose(vehiclePosition, vehicleRotation),
        unfolded: { position: spreadPosition, quaternion: robotPose.quaternion.clone() }, robot: robotPose });
    }
    function createCarrier(name, far, near) {
      var result = group(name, root);
      parts[name].root = result;
      carriers[name] = { object: result, far: new THREE.Vector3().fromArray(far),
        near: new THREE.Vector3().fromArray(near) };
      return result;
    }
    function codeMark(parent, position) {
      var mark = group('', parent); mark.position.fromArray(position);
      box(mark, [3.6, 3.5, 0.12], 'black', [0, 0, 0]);
      [-1, 1].forEach(function (side) {
        box(mark, [0.2, 1.1, 0.13], 'silver', [side * 1.04, 0.43, 0.13], [0, 0, side * 0.65]);
        box(mark, [0.2, 1.1, 0.13], 'silver', [side * 1.04, -0.43, 0.13], [0, 0, -side * 0.65]);
      });
      box(mark, [0.22, 2.2, 0.13], 'silver', [0, 0, 0.13], [0, 0, -0.22]);
    }
    var jet = createCarrier('geminiJet', [-22, 5, -10], [0, 5, -6]);
    var ship = createCarrier('gptShip', [0, 0, 6], [0, 0, 3]);
    var bike = createCarrier('claudeBike', [24, 0, 4], [0, 0, 7]);

    // GPT ship: torso, reversible chest, shoulders, pelvis, and both hull/leg assemblies.
    var torso = group('gptShip.chestFrame', ship);
    polygon(torso, [[-4.4, 2.7], [4.4, 2.7], [4.4, -1.4], [3, -2.8], [-3, -2.8], [-4.4, -1.4]],
      4.4, 'darkGray');
    box(torso, [7.2, 4.4, 4.55], 'silver', [0, 0.1, 0]);
    box(torso, [6.3, 0.65, 4.7], 'black', [0, -2.5, 0]);
    // Scale the entire chest assembly in depth, including its plate and hinge offset.
    torso.scale.z = 1.5;
    track(torso, [0, 3, -1.5], [-Math.PI / 2, 0, 0], [0, 21, 0]);
    var chestPlate = group('gptShip.chestPlate', torso);
    // One reversible leaf: the hinge runs along its top edge, with two laminated faces.
    chestPlate.position.set(0, 2.65, 2.5);
    var plateOutline = [[-4.3, 0], [4.3, 0], [4.3, -4.2], [3, -5.3], [-3, -5.3], [-4.3, -4.2]];
    polygon(chestPlate, plateOutline, 0.24, 'antigravityBlue', [0, 0, 0.13]);
    polygon(chestPlate, plateOutline, 0.24, 'silver', [0, 0, -0.13]);
    box(chestPlate, [3.5, 3.4, 0.13], 'white', [0, -2.35, 0.33]);
    var emblem = group('gptShip.chestEmblem', chestPlate);
    emblem.position.set(0, -2.25, 0.44);
    polygon(emblem, [[-1.3, -0.8], [-0.9, 0.25], [-0.55, 0.25], [-0.35, 0.95],
      [0.4, 0.95], [0.75, 0.15], [1.05, 0.15], [1.25, -0.8], [0.9, -0.8],
      [0.65, -0.2], [0.35, -0.2], [0.1, 0.55], [-0.1, 0.55], [-0.3, -0.15],
      [-0.65, -0.15], [-0.9, -0.8]], 0.07, 'antigravityBlue');
    ['wingRed', 'wingYellow', 'wingGreen'].forEach(function (key, index) {
      box(emblem, [0.35, 0.35, 0.08], key, [0.65 + index * 0.27, 1.08 - index * 0.47, 0], [0, 0, 0.6]);
    });
    var waist = group('gptShip.waist', ship);
    waist.scale.z = 1.5;
    cylinder(waist, 2.8, 3.1, 1.4, 'black', [0, 1.1, 0], null, 8);
    box(waist, [6.8, 2.1, 3.9], 'darkGray', [0, -0.2, 0]);
    polygon(waist, [[-1.3, 1], [1.3, 1], [0.8, -2.7], [-0.8, -2.7]], 0.8, 'darkGray', [0, 0, 2.25]);
    [-1, 1].forEach(function (side) {
      box(waist, [2.3, 2.1, 1.1], 'darkGray', [side * 2.6, -0.5, 2.0], [0, 0, side * 0.12]);
    });
    track(waist, [0, 2.7, -5.4], [Math.PI / 2, 0, 0], [0, 16.1, 0]);

    ['L', 'R'].forEach(function (suffix, index) {
      var side = index ? 1 : -1;
      var shoulder = group('gptShip.shoulderBlock' + suffix, ship);
      box(shoulder, [4.6, 4.7, 4.6], 'darkGray');
      codeMark(shoulder, [0, 0, 2.36]);
      track(shoulder, [side * 5.5, 2.5, -2.8], [0, 0, 0], [side * 6.65, 23.0, 0], null, [side * 2, 1.5, 0]);
      var leg = group('gptShip.thigh' + suffix, ship);
      box(leg, [3.0, 4.3, 3.1], 'white', [0, -2.0, 0]);
      cylinder(leg, 1.4, 1.4, 3.2, 'black', [0, -4.2, 0], [0, 0, Math.PI / 2]);
      var shin = group('gptShip.shin' + suffix, leg); shin.position.set(0, -8, 0);
      polygon(shin, [[-1.65, 4.1], [1.65, 4.1], [2.55, -4.1], [-2.55, -4.1]], 4.3, 'darkGray');
      polygon(shin, [[-1.5, 1.4], [1.5, 1.4], [1.15, -0.9], [0, -1.65], [-1.15, -0.9]],
        0.65, 'white', [0, 3.8, 2.1]);
      var blueMaterial = material('antigravityBlue', true);
      blueMaterial.emissive.set(palette.antigravityBlue); blueMaterial.emissiveIntensity = 0;
      glowMaterials.push({ material: blueMaterial, sole: false });
      box(shin, [3.2, 5.6, 0.18], 'antigravityBlue', [0, -0.35, 2.25], null, blueMaterial);
      [-1, 1].forEach(function (railSide) {
        box(shin, [0.17, 6.2, 0.22], 'silver', [railSide * 1.7, -0.3, 2.45]);
      });
      var armor = group('gptShip.shinArmor' + suffix, shin);
      armor.position.set(0, -0.35, 2.65);
      var panels = [];
      [-1, 1].forEach(function (panelSide) {
        var panel = group('', armor);
        panel.position.x = panelSide * 0.88;
        polygon(panel, [[-0.88, 3.2], [0.88, 3.2], [1.15, -3.2], [-1.15, -3.2]], 0.55, 'darkGray');
        panels.push({ object: panel, side: panelSide });
      });
      shinJoints.push(panels);
      var ankle = group('gptShip.ankle' + suffix, leg); ankle.position.set(0, -12.45, 0);
      var foot = group('gptShip.foot' + suffix, ankle); foot.position.set(0, -1.15, 1.0);
      footJoints.push(ankle);
      box(foot, [4.8, 2.3, 6.1], 'darkGray');
      polygon(foot, [[-2.4, -0.65], [2.4, -0.65], [1.8, 0.85], [-1.8, 0.85]], 1.4,
        'darkGray', [0, 0, 3.1]);
      var soleMaterial = material('darkGray', true);
      soleMaterial.emissive.set(palette.antigravityBlue);
      soleMaterial.emissiveIntensity = 0;
      glowMaterials.push({ material: soleMaterial, sole: true });
      var sole = group('gptShip.sole' + suffix, foot);
      box(sole, [4.9, 0.17, 6.2], 'darkGray', [0, -1.18, 0], null, soleMaterial);
      // Boot U-light is intentionally left to compositing; there is no carved boot logo.
      for (var vent = 0; vent < 3; vent++) {
        box(shin, [0.15, 0.18, 1.5], 'black', [side * 2.25, vent * 0.45 - 1.5, 0]);
      }
      track(leg, [side * 3.15, 3.0, -6.8], [-Math.PI / 2, 0, 0],
        [side * 3.05, 15, 0], null, [side * 1.8, 2, 0]);
      // Two joined bow halves make a pointed hull and remain as calf-side fairings.
      var bow = group('gptShip.bowFairing' + suffix, ship);
      polygon(bow, [[0, 4.8], [side * 5.7, 0], [0, 0]], 1.1, 'darkGray');
      polygon(bow, [[0, 4.35], [side * 4.95, 0.3], [0, 0.3]], 0.12,
        'silver', [0, 0, -0.62]);
      track(bow, [0, 2.2, 9.2], [Math.PI / 2, 0, 0],
        [side * 5.55, 5.4, 2.5], [0, side * Math.PI / 2, 0], [side * 2, 1, -1]);
    });

    // Gemini jet: the helmet nose remains the same object in both configurations.
    var back = group('geminiJet.back', jet);
    polygon(back, [[-3.1, 3.7], [3.1, 3.7], [3.1, -2.7], [0, -6.8], [-3.1, -2.7]], 2.2, 'antigravityBlue');
    box(back, [5, 4.4, 0.45], 'antigravityBlue', [0, 0.8, -1.25]);
    track(back, [0, 2.0, 0], [-Math.PI / 2, 0, 0], [0, 21.9, -3.25], null, [0, 1, -2]);
    var helmet = group('geminiJet.helmetNose', jet);
    box(helmet, [2.6, 2.6, 2.5], 'antigravityBlue', [0, 0.1, -0.2]);
    polygon(helmet, [[-1.1, -1.2], [1.1, -1.2], [0.7, 1.6], [0, 2], [-0.7, 1.6]],
      1.1, 'antigravityBlue', [0, 0, -1.6]);
    box(helmet, [2.3, 1.5, 0.45], 'black', [0, -0.1, 1.18]);
    [-1, 1].forEach(function (side) {
      box(helmet, [0.7, 0.19, 0.12], 'white', [side * 0.56, 0.13, 1.46], [0, 0, side * 0.17]);
      polygon(helmet, [[0, -0.15], [side * 1.85, 1.8], [side * 1.42, 0.3], [0, -0.62]],
        0.25, 'white', [0, 0.55, 1.3]);
      var duct = group('geminiJet.earDuct' + (side < 0 ? 'L' : 'R'), helmet);
      duct.position.set(side * 1.65, -0.1, 0.3);
      box(duct, [1.0, 1.55, 2.0], 'antigravityBlue');
      box(duct, [0.74, 1.17, 0.15], 'black', [0, 0, 1.02]);
      [-1, 1].forEach(function (edge) {
        box(duct, [0.13, 1.35, 0.2], 'white', [edge * 0.42, 0, 1.12]);
        box(duct, [0.9, 0.13, 0.2], 'white', [0, edge * 0.64, 1.12]);
      });
      for (var grille = 0; grille < 4; grille++) {
        box(duct, [0.64, 0.08, 0.08], 'silver', [0, grille * 0.25 - 0.37, 1.09]);
      }
      polygon(helmet, [[0, 0.3], [side * 0.75, -1.65], [side * 0.25, -1.4]],
        0.4, 'antigravityBlue', [side * 1.3, -0.3, 0]);
    });
    var forehead = group('geminiJet.forehead', helmet); forehead.position.set(0, 1.45, 0.4);
    var foreheadShape = new THREE.Shape();
    foreheadShape.moveTo(-0.65, -0.55); foreheadShape.lineTo(0.65, -0.55);
    foreheadShape.lineTo(0.65, 0.75); foreheadShape.quadraticCurveTo(0, 1.15, -0.65, 0.75);
    foreheadShape.closePath();
    var groove = new THREE.Path();
    groove.moveTo(-0.4, -0.35); groove.lineTo(-0.4, 0.35);
    groove.quadraticCurveTo(-0.4, 0.8, 0, 0.8);
    groove.quadraticCurveTo(0.4, 0.8, 0.4, 0.35);
    groove.lineTo(0.4, -0.35); groove.lineTo(0.23, -0.35); groove.lineTo(0.23, 0.35);
    groove.quadraticCurveTo(0.23, 0.6, 0, 0.6);
    groove.quadraticCurveTo(-0.23, 0.6, -0.23, 0.35);
    groove.lineTo(-0.23, -0.35); groove.closePath();
    foreheadShape.holes.push(groove);
    surface(forehead, new THREE.ExtrudeGeometry(foreheadShape, { depth: 0.32, bevelEnabled: false }),
      'antigravityBlue');
    box(forehead, [1.2, 1.3, 0.08], 'black', [0, 0.1, -0.08]);
    var faceplate = group('geminiJet.faceplate', helmet);
    faceplate.position.set(0, -1.15, 1.38);
    polygon(faceplate, [[-0.95, 1.1], [0, 0.85], [0.95, 1.1], [0.65, 0], [0, -0.3], [-0.65, 0]],
      0.3, 'silver');
    box(faceplate, [0.1, 0.65, 0.08], 'black', [0, 0.35, 0.19]);
    track(helmet, [0, 2.15, 8.0], [0, Math.PI, 0], [0, 27.9, 0.3], null, [0, 4, 0]);
    ['L', 'R'].forEach(function (suffix, index) {
      var side = index ? 1 : -1;
      var thruster = group('geminiJet.backThruster' + suffix, jet);
      cylinder(thruster, 1.4, 1.15, 4.8, 'antigravityBlue');
      cylinder(thruster, 1.26, 1.26, 0.15, 'black', [0, 2.43, 0]);
      cylinder(thruster, 0.77, 0.77, 0.16, 'darkGray', [0, 2.52, 0]);
      box(thruster, [0.13, 0.16, 2.1], 'silver', [0, 2.61, 0]);
      box(thruster, [2.1, 0.16, 0.13], 'silver', [0, 2.61, 0]);
      track(thruster, [side * 3.1, 2.0, -3.0], [-Math.PI / 2, 0, 0],
        [side * 3.5, 24.5, -4.1], null, [side, 2, -1]);
      var wingRoot = group('geminiJet.wingRoot' + suffix, jet);
      var wing = group('geminiJet.wing' + suffix, wingRoot);
      cylinder(wingRoot, 0.65, 0.65, 1.5, 'darkGray', [0, 0, 0], [0, 0, Math.PI / 2]);
      function points(values) { return values.map(function (point) { return [point[0] * side, point[1]]; }); }
      polygon(wing, points([[0, 0], [9.8, 6.5], [10.4, 3.9], [1.6, -2.3]]), 0.55, 'antigravityBlue');
      polygon(wing, points([[0.65, 0.05], [9.45, 5.85], [9.95, 3.9], [1.8, -1.6]]), 0.64, 'white');
      polygon(wing, points([[0, 0], [9.8, 6.5], [9.55, 5.7], [0.8, -0.1]]), 0.78, 'wingRed');
      polygon(wing, points([[9.8, 6.5], [10.4, 3.9], [9.8, 3.6], [9.25, 6.0]]), 0.8, 'wingYellow');
      polygon(wing, points([[10.4, 3.9], [1.6, -2.3], [1.8, -1.5], [9.85, 4.15]]), 0.78, 'wingGreen');
      wingJoints.push(wing);
      track(wingRoot, [side * 2.5, 2.0, -0.6], null, [side * 4.2, 23.9, -2.6], null, [side * 2, 2, -1]);
    });

    // Claude bike: two permanent arm modules, plus wheels/seat/handlebar that stow behind them.
    ['L', 'R'].forEach(function (suffix, index) {
      var side = index ? 1 : -1;
      var frame = group('claudeBike.armFrame' + suffix, bike);
      cylinder(frame, 1.1, 1.1, 2.4, 'black', [0, -0.6, 0]);
      box(frame, [2.3, 2.6, 2.1], 'silver', [0, -1.0, 0]);
      var innerFrame = group('claudeBike.innerFrame' + suffix, frame);
      box(innerFrame, [1.7, 3.5, 1.6], 'silver', [0, 0, 0]);
      var forearm = group('claudeBike.forearm' + suffix, frame);
      cylinder(forearm, 1.65, 1.5, 5.5, 'darkGray');
      var cowl = group('claudeBike.cowl' + suffix, forearm);
      // Longitudinal fairing hinge runs down the outer edge, along local Y.
      cowl.position.set(side * 1.95, 0, -1.3);
      var shellCenter = [-side * 1.95, 0, 1.3];
      box(cowl, [3.9, 5.45, 0.45], 'claudeRed', [shellCenter[0], 0, 3.1]);
      box(cowl, [0.55, 5.45, 3.2], 'claudeRed', [shellCenter[0] - 1.7, 0, 1.45]);
      box(cowl, [0.55, 5.45, 3.2], 'claudeRed', [shellCenter[0] + 1.7, 0, 1.45]);
      box(cowl, [3.9, 0.55, 3.4], 'claudeRed', [shellCenter[0], 2.45, 1.55]);
      var gauge = group('claudeBike.gauge' + suffix, cowl);
      gauge.position.set(shellCenter[0] + side * 1.15, 0, 3.39);
      box(gauge, [0.62, 4.65, 0.15], 'black');
      for (var cellIndex = 0; cellIndex < 10; cellIndex++) {
        var cellMaterial = material('white', true);
        box(gauge, [0.43, 0.36, 0.08], 'white', [0, 2.02 - cellIndex * 0.45, 0.13], null, cellMaterial, false);
        cells.push({ material: cellMaterial, index: cellIndex });
      }
      var gaugeText = label(cowl, 'session limit', 2.5, 0.46, [shellCenter[0] - side * 0.12, 1.88, 3.4]);
      if (gaugeText) gaugeLabels.push(gaugeText);
      cowlJoints.push({ object: cowl, side: side });
      var handHinge = group('claudeBike.handHinge' + suffix, forearm);
      handHinge.position.set(0, -2.75, 0.4);
      var hand = group('claudeBike.hand' + suffix, handHinge); hand.position.set(0, -0.8, -0.25);
      handJoints.push(handHinge);
      box(hand, [2.55, 1.7, 2.0], 'black');
      for (var finger = 0; finger < 4; finger++) {
        box(hand, [0.49, 0.9, 0.55], 'darkGray', [(finger - 1.5) * 0.57, -0.45, 1.08]);
      }
      box(hand, [0.65, 1.25, 0.85], 'darkGray', [-side * 1.35, 0, 0.38], [0, 0, side * 0.25]);
      var rotor = group('claudeBike.clawRotor' + suffix, forearm);
      rotor.position.set(0, -2.75, 0.2);
      cylinder(rotor, 1.42, 1.42, 0.7, 'black');
      var bladeCarrier = group('claudeBike.bladeCarrier' + suffix, rotor);
      // Full-size blades slide down from storage after the fist folds into the forearm.
      for (var blade = 0; blade < 3; blade++) {
        var bladePart = group('claudeBike.claw' + suffix + (blade + 1), bladeCarrier);
        // Broad side profile, narrow back-of-hand profile; the bevel points toward the wrist back.
        polygon(bladePart, [[-0.55, 0], [0.55, 0], [0.55, -4.9], [-0.5, -6.2], [-0.55, -5.7]],
          0.28, 'silver', [(blade - 1) * 0.9, 0, 0.85], [0, -Math.PI / 2, 0]);
      }
      clawJoints.push(bladeCarrier);
      armJoints.push({ forearm: forearm, inner: innerFrame });
      // Front/rear modules share the centerline, leaving two readable wheels in profile.
      track(frame, [0, 3.0, -side * 0.3], [-Math.PI / 2, 0, side < 0 ? 0 : Math.PI],
        [side * 7.8, 20.6, 0], [0, 0, side * 0.035], [side * 4, 0, 2]);
      var wheel = group('claudeBike.wheel' + suffix, bike);
      cylinder(wheel, 2.1, 2.1, 0.85, 'black', null, [0, 0, Math.PI / 2], 16);
      cylinder(wheel, 1.25, 1.25, 0.91, 'silver', null, [0, 0, Math.PI / 2], 12);
      cylinder(wheel, 0.35, 0.35, 0.97, 'black', null, [0, 0, Math.PI / 2]);
      track(wheel, [0, 2.1, side * 6.6], null, [side * 7.8, 16.4, -2.1],
        [0, Math.PI / 2, 0], [side * 4, 0, 3]);
    });
    var saddle = group('claudeBike.saddle', bike);
    box(saddle, [2.4, 0.55, 3.0], 'black');
    box(saddle, [1.6, 0.9, 1.5], 'claudeRed', [0, -0.4, -1.1]);
    track(saddle, [0, 6.1, -2.5], null, [7.8, 17.6, -2.9], [Math.PI / 2, 0, 0], [4, 0, 3]);
    var handlebar = group('claudeBike.handlebar', bike);
    box(handlebar, [3.5, 0.3, 0.3], 'black');
    box(handlebar, [0.3, 1.3, 0.3], 'silver', [0, -0.6, 0]);
    track(handlebar, [0, 6.25, 2.3], null, [-7.8, 18.6, -2.6], [0, 0, Math.PI / 2], [-4, 0, 3]);
    var frontFairing = group('claudeBike.frontFairing', bike);
    polygon(frontFairing, [[-1.65, -1.1], [1.65, -1.1], [1.2, 1.25], [-1.2, 1.25]], 1.1, 'claudeRed');
    box(frontFairing, [1.75, 0.65, 0.15], 'white', [0, -0.25, 0.65]);
    polygon(frontFairing, [[-1, 0.4], [1, 0.4], [0.75, 2.25], [-0.75, 2.25]],
      0.15, 'black', [0, 0, 0.2], [-0.28, 0, 0]);
    track(frontFairing, [0, 5.2, 5.0], [-0.2, 0, 0], [7.8, 19.3, -2.5],
      [0, Math.PI, 0], [4, 1, 3]);
    ['L', 'R'].forEach(function (suffix, index) {
      var side = index ? 1 : -1;
      var fork = group('claudeBike.fork' + suffix, bike);
      cylinder(fork, 0.17, 0.17, 4.2, 'silver');
      track(fork, [side * 0.7, 3.3, 5.8], [-0.32, 0, 0],
        [side * 7.8, 18.1, -2.0], null, [side * 4, 0, 3]);
    });

    function applyMechanisms() {
      var motion = state.mechanisms;
      shinJoints.forEach(function (panels) {
        panels.forEach(function (panel) {
          panel.object.position.x = panel.side * (0.88 + motion.shinSlide * 1.75);
          panel.object.position.z = motion.shinSlide * 0.25;
        });
      });
      glowMaterials.forEach(function (entry) {
        // Modest linear-light emission avoids clipping blue into bright cyan.
        entry.material.emissiveIntensity = motion.shinSlide * 0.3;
        if (entry.sole) entry.material.color.set(palette.darkGray).lerp(new THREE.Color(palette.antigravityBlue), motion.shinSlide);
        else entry.material.color.set(palette.antigravityBlue).multiplyScalar(1 - motion.shinSlide * 0.3);
      });
      cowlJoints.forEach(function (joint) {
        joint.object.rotation.y = joint.side * (1 - motion.cowlFold) * 0.22;
      });
      handJoints.forEach(function (joint) {
        var fold = Math.max(1 - phase(state.fusion, 0.3, 0.7), phase(motion.clawSpinOut, 0, 0.45));
        joint.rotation.x = fold * Math.PI;
      });
      clawJoints.forEach(function (joint) {
        joint.position.y = 6.25 * (1 - phase(motion.clawSpinOut, 0.3, 1));
      });
      wingJoints.forEach(function (wing) { wing.rotation.x = -(1 - motion.wingHinge) * Math.PI / 2; });
      faceplate.rotation.x = (1 - motion.faceplateClose) * Math.PI * 0.57;
      // The silver ship deck swings around its top-edge hinge into the blue robot chest.
      chestPlate.rotation.x = Math.PI * (1 - motion.chestPlateFlip);
    }
    function ensureAlive() { if (disposed) throw new Error('This robot has been disposed.'); }
    function setFusion(value) {
      ensureAlive(); state.fusion = bounded(value, 1);
      var t = state.fusion, approach = phase(t, 0, 0.3);
      var unfold = phase(t, 0.3, 0.7), dock = phase(t, 0.7, 1);
      Object.keys(carriers).forEach(function (key) {
        var carrier = carriers[key];
        carrier.object.position.copy(carrier.far).lerp(carrier.near, approach).multiplyScalar(1 - dock);
      });
      tracks.forEach(function (entry) {
        entry.part.position.copy(entry.vehicle.position).lerp(entry.unfolded.position, unfold).lerp(entry.robot.position, dock);
        entry.part.quaternion.copy(entry.vehicle.quaternion).slerp(entry.unfolded.quaternion, unfold).slerp(entry.robot.quaternion, dock);
      });
      armJoints.forEach(function (joint) {
        joint.inner.position.y = -1.3 - unfold * 1.6;
        joint.forearm.position.y = -2.7 - unfold * 2.5;
      });
      // Hull bows become boots around the ankle hinge during the unfolding stage.
      footJoints.forEach(function (joint) { joint.rotation.x = (1 - unfold) * Math.PI / 2; });
      Object.assign(state.mechanisms, {
        shinSlide: 0, cowlFold: phase(t, 0.37, 0.7), clawSpinOut: 0,
        wingHinge: phase(t, 0.34, 0.7), faceplateClose: phase(t, 0.82, 0.97),
        chestPlateFlip: phase(t, 0.78, 0.98)
      });
      applyMechanisms(); root.updateMatrixWorld(true);
      return api;
    }
    function setMechanism(name, value) {
      ensureAlive();
      if (MECHANISMS.indexOf(name) < 0) throw new RangeError('Unknown mechanism: ' + name);
      state.mechanisms[name] = bounded(value, 1);
      applyMechanisms(); root.updateMatrixWorld(true);
      return api;
    }
    function setScaling(value) {
      ensureAlive(); state.scaling = bounded(value, 1);
      root.scale.setScalar(THREE.MathUtils.lerp(humanScale, 1, smooth(state.scaling)));
      root.updateMatrixWorld(true); return api;
    }
    function setGauge(value) {
      ensureAlive(); state.gauge = Math.round(bounded(value, 10));
      cells.forEach(function (cell) {
        var active = cell.index < state.gauge;
        var key = !active ? 'white' : state.gauge < 8 ? 'gaugeYellow' : 'claudeRed';
        cell.material.color.set(palette[key]);
      });
      root.userData.gaugeStatus = state.gauge >= 10 ? 'LIMIT REACHED — WAIT FOR RESET' :
        state.gauge >= 8 ? 'NEAR LIMIT' : 'AVAILABLE';
      return api;
    }
    function getState() {
      return { fusion: state.fusion, scaling: state.scaling, gauge: state.gauge,
        mechanisms: Object.assign({}, state.mechanisms), gaugeStatus: root.userData.gaugeStatus };
    }
    function dispose() {
      if (disposed) return;
      geometries.forEach(function (geometry) { geometry.dispose(); });
      materials.forEach(function (entry) { entry.dispose(); });
      textures.forEach(function (texture) { texture.dispose(); });
      root.removeFromParent(); disposed = true;
    }
    var api = { root: root, parts: parts, palette: Object.freeze(palette),
      setFusion: setFusion, setMechanism: setMechanism, setScaling: setScaling,
      setGauge: setGauge, getState: getState, dispose: dispose };
    setFusion(0);
    bounds.setFromObject(bike); bounds.getSize(scratch);
    humanScale = 2 / scratch.z;
    root.userData.humanScale = humanScale;
    root.userData.vehicleBikeLength = scratch.z;
    setFusion(1); setScaling(1); setGauge(1);
    root.userData.partOrigins = {
      geminiJet: 'Helmet nose, back, wings, back thrusters',
      gptShip: 'Chest, shoulders, waist, thighs, shins, feet',
      claudeBike: 'Arm frames, cowls, hands, gauges, claws, stowed wheels'
    };
    return api;
  }
  global.AntigravityKing = Object.freeze({ build: build, defaultPalette: DEFAULT_PALETTE,
    mechanismNames: MECHANISMS, version: '2.0.0' });
})(window);
