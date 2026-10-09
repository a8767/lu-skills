import sys, json
sys.path.insert(0, 'tools')
from ld import LD

ld = LD()
print('period:', ld.period_text())

# 列出日期选择器区域内的关键子元素（图标/触发/选项/年份）
js = (
    "(function(){"
    "try{"
    "var root=document.querySelector('[class*=advanced-date-picker]');"
    "if(!root)return 'NO_ROOT';"
    "var kids=root.querySelectorAll('*');"
    "var out=[];"
    "for(var i=0;i<kids.length && out.length<40;i++){"
    "  var e=kids[i];"
    "  var cls=(e.getAttribute('class')||'');"
    "  var t=e.textContent.trim().slice(0,14);"
    "  var low=cls.toLowerCase();"
    "  if(low.indexOf('icon')>=0||low.indexOf('calendar')>=0||low.indexOf('trigger')>=0||low.indexOf('suffix')>=0||low.indexOf('caret')>=0||low.indexOf('arrow')>=0||t==='自定义'||t==='近7日'||t==='近30日'||t==='自然月'||t==='本月'||t==='上月'||cls.indexOf('range')>=0){"
    "    out.push(e.tagName+' | '+cls.slice(0,45)+' | '+t);"
    "  }"
    "}"
    "return out.join(' @@ ');"
    "}catch(err){return 'ERR:'+err.message;}"
    "})()"
)
print('PICKER ELEMENTS:')
print(ld.eval(js))
ld.screenshot('out/debug/page_current.png')
print('screenshot saved')
ld.close()
