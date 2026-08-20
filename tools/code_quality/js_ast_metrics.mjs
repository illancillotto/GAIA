#!/usr/bin/env node
import fs from 'node:fs';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
let parser;
try {
  parser = require('@babel/parser');
} catch (error) {
  console.error(JSON.stringify({ error: `missing @babel/parser: ${error.message}` }));
  process.exit(2);
}

const file = process.argv[2];
if (!file) {
  console.error(JSON.stringify({ error: 'missing file path' }));
  process.exit(2);
}

const source = fs.readFileSync(file, 'utf8');
const lines = source.split(/\r?\n/);

function parse() {
  return parser.parse(source, {
    sourceType: 'module',
    errorRecovery: true,
    plugins: [
      'typescript',
      'jsx',
      'decorators-legacy',
      'classProperties',
      'classPrivateProperties',
      'classPrivateMethods',
      'objectRestSpread',
      'optionalChaining',
      'nullishCoalescingOperator',
      'dynamicImport',
      'topLevelAwait',
    ],
  });
}

function childrenOf(node) {
  const out = [];
  if (!node || typeof node !== 'object') return out;
  for (const [key, value] of Object.entries(node)) {
    if (key === 'loc' || key === 'start' || key === 'end' || key === 'extra' || key === 'leadingComments' || key === 'trailingComments' || key === 'innerComments') continue;
    if (Array.isArray(value)) {
      for (const item of value) if (item && typeof item.type === 'string') out.push(item);
    } else if (value && typeof value.type === 'string') {
      out.push(value);
    }
  }
  return out;
}

function effectiveLoc(start, end) {
  let count = 0;
  for (let i = Math.max(0, start - 1); i < Math.min(lines.length, end); i += 1) {
    const t = lines[i].trim();
    if (t && !t.startsWith('//') && !t.startsWith('/*') && !t.startsWith('*')) count += 1;
  }
  return count;
}

function hashNode(node) {
  function clean(n) {
    if (!n || typeof n !== 'object') return n;
    if (Array.isArray(n)) return n.map(clean);
    const o = { type: n.type };
    for (const [k, v] of Object.entries(n)) {
      if (['loc', 'start', 'end', 'extra', 'leadingComments', 'trailingComments', 'innerComments'].includes(k)) continue;
      if (k === 'id' && v && typeof v === 'object') { o.id = { type: v.type }; continue; }
      if (v && typeof v.type === 'string') o[k] = clean(v);
      else if (Array.isArray(v)) o[k] = v.map(clean);
      else if (['operator', 'kind', 'async', 'generator', 'computed', 'optional'].includes(k)) o[k] = v;
    }
    return o;
  }
  return crypto.createHash('sha256').update(JSON.stringify(clean(node))).digest('hex').slice(0, 16);
}

function paramCount(node) {
  return Array.isArray(node.params) ? node.params.length : 0;
}

function calleeName(callee) {
  if (!callee) return 'callback';
  if (callee.type === 'Identifier') return callee.name;
  if (callee.type === 'MemberExpression') {
    const object = callee.object?.name || callee.object?.property?.name || callee.object?.type || 'object';
    const property = callee.property?.name || callee.property?.value || 'member';
    return `${object}.${property}`;
  }
  return callee.type || 'callback';
}

function nearestAncestor(ancestors, type) {
  for (let i = ancestors.length - 1; i >= 0; i -= 1) {
    if (ancestors[i]?.type === type) return ancestors[i];
  }
  return null;
}

function callbackContextName(node, parent, ancestors) {
  const variable = nearestAncestor(ancestors, 'VariableDeclarator');
  const property = nearestAncestor(ancestors, 'ObjectProperty') || nearestAncestor(ancestors, 'ClassProperty');
  const call = parent?.type === 'CallExpression' ? parent : nearestAncestor(ancestors, 'CallExpression');
  const owner = variable?.id?.name || property?.key?.name || property?.key?.value || null;
  if (call) {
    const argIndex = Array.isArray(call.arguments) ? call.arguments.indexOf(node) : -1;
    const suffix = `${calleeName(call.callee)}[${argIndex < 0 ? 'n' : argIndex}]<callback>`;
    return owner ? `${owner}:${suffix}` : suffix;
  }
  return owner ? `${owner}<callback>` : 'callback<callback>';
}

function callableName(node, parent, key, ancestors = []) {
  if (node.id?.name) return node.id.name;
  if ((node.type === 'ClassMethod' || node.type === 'ClassPrivateMethod' || node.type === 'ObjectMethod') && node.key) return node.key.name || node.key.value || '<method>';
  if (parent?.type === 'VariableDeclarator' && parent.id?.name) return parent.id.name;
  if (parent?.type === 'AssignmentExpression') return parent.left?.name || parent.left?.property?.name || '<assignment>';
  if (parent?.type === 'ObjectProperty' || parent?.type === 'ClassProperty') return parent.key?.name || parent.key?.value || '<property>';
  if (parent?.type === 'CallExpression') return callbackContextName(node, parent, ancestors);
  return key ? `${key}<anonymous>` : '<anonymous>';
}

function callableKind(node, name) {
  if (node.async) return 'async_function';
  if (node.type?.includes('Method')) return 'method';
  if (/^[A-Z]/.test(name)) return 'react_component';
  if (node.type === 'ArrowFunctionExpression') return 'arrow_function';
  return 'function';
}

const decisionTypes = new Set(['IfStatement', 'ForStatement', 'ForInStatement', 'ForOfStatement', 'WhileStatement', 'DoWhileStatement', 'SwitchStatement', 'SwitchCase', 'CatchClause', 'ConditionalExpression', 'LogicalExpression']);
const nestingTypes = new Set(['IfStatement', 'ForStatement', 'ForInStatement', 'ForOfStatement', 'WhileStatement', 'DoWhileStatement', 'SwitchStatement', 'CatchClause']);

function complexities(root) {
  let cyclomatic = 1;
  let cognitive = 0;
  let maxNesting = 0;
  function walk(node, nesting = 0) {
    if (!node || typeof node !== 'object') return;
    const isDecision = decisionTypes.has(node.type);
    if (isDecision) {
      cyclomatic += 1;
      cognitive += 1 + nesting;
    }
    const inc = nestingTypes.has(node.type);
    const next = inc ? nesting + 1 : nesting;
    if (inc) maxNesting = Math.max(maxNesting, next);
    for (const child of childrenOf(node)) walk(child, next);
  }
  walk(root, 0);
  return { cyclomatic, cognitive, nesting: maxNesting };
}

function walkAll(node, parent = null, key = '', ancestors = []) {
  if (!node || typeof node !== 'object') return;
  const callableTypes = new Set(['FunctionDeclaration', 'FunctionExpression', 'ArrowFunctionExpression', 'ObjectMethod', 'ClassMethod', 'ClassPrivateMethod']);
  if (callableTypes.has(node.type)) {
    const name = callableName(node, parent, key, ancestors);
    const startLine = node.loc?.start?.line || 1;
    const endLine = node.loc?.end?.line || startLine;
    const c = complexities(node.body || node);
    callables.push({
      path: '',
      name,
      kind: callableKind(node, name),
      line: startLine,
      end_line: endLine,
      cyclomatic: c.cyclomatic,
      cognitive: c.cognitive,
      loc: effectiveLoc(startLine, endLine),
      nesting: c.nesting,
      params: paramCount(node),
      fingerprint: hashNode(node),
      violations: [],
    });
  }
  for (const child of childrenOf(node)) walkAll(child, node, key || node.type, [...ancestors, node]);
}

let ast;
try {
  ast = parse();
} catch (error) {
  console.error(JSON.stringify({ error: error.message }));
  process.exit(2);
}

const callables = [];
walkAll(ast.program);
const fileMetrics = {
  imports: (source.match(/\bimport\b|\brequire\s*\(/g) || []).length,
  loc: effectiveLoc(1, lines.length),
  useState: (source.match(/\buseState\s*\(/g) || []).length,
  useEffect: (source.match(/\buseEffect\s*\(/g) || []).length,
  useReducer: (source.match(/\buseReducer\s*\(/g) || []).length,
};
console.log(JSON.stringify({ callables, file_metrics: fileMetrics }));
