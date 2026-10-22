// 브라우저 대신 작은 가짜 화면을 사용한다. 실제 화면 모양은 검증하지 않는다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup(fetch) {
  const elements = new Map();
  const context = vm.createContext({
    document: { addEventListener() {}, getElementById(id) {
      if (!elements.has(id)) elements.set(id, { innerHTML: '' });
      return elements.get(id);
    } }, window: {}, fetch, console
  });
  vm.runInContext(fs.readFileSync('public/js/main.js', 'utf8'), context);
  return { context, elements };
}
test('API의 HTTP 오류를 표시할 수 있도록 예외로 전달한다', async () => {
  const { context } = setup(async () => ({ ok: false, status: 503 }));
  await assert.rejects(context.fetchAPI('/test'), /503/);
});
test('success=false와 서버 메시지를 처리한다', async () => {
  const { context } = setup(async () => ({ ok: true, json: async () => ({ success: false, message: 'DB 실패' }) }));
  await assert.rejects(context.fetchAPI('/test'), /DB 실패/);
});
test('정상 API 응답을 그대로 돌려준다', async () => {
  const data = { success: true, data: [] };
  const { context } = setup(async () => ({ ok: true, json: async () => data }));
  assert.equal(await context.fetchAPI('/test'), data);
});
test('관측 자료가 없으면 빈 상태 안내를 표시한다', () => {
  const { context, elements } = setup();
  context.renderNationalWeather([]);
  assert.match(elements.get('nationalWeatherSummary').innerHTML, /관측 데이터가 없습니다/);
});
test('숫자 문자열의 평균·최고·최저 기온을 계산한다', () => {
  const { context, elements } = setup();
  context.renderNationalWeather([{ region_name: '서울', temperature: '10' }, { region_name: '부산', temperature: '20' }]);
  const html = elements.get('nationalWeatherSummary').innerHTML;
  assert.match(html, /15\.0℃/);
  assert.match(html, /부산\s+20℃/);
  assert.match(html, /서울\s+10℃/);
});
