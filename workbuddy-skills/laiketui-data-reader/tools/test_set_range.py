import sys, json
sys.path.insert(0, 'tools')
from ld import LD

def click_by_text_exact(ld, txt):
    js = f'''
(function(){{
  var all=[].slice.call(document.querySelectorAll('*'));
  for(var i=0;i<all.length;i++){{
    var e=all[i];
    if(e.children.length===0 && e.textContent.trim()==={json.dumps(txt)}){{
      var el=e;
      for(var j=0;j<8 && el;j++){{
        el=el.parentElement;
        if(el && (el.tagName==='BUTTON' || el.getAttribute('role')==='button' || (el.getAttribute('class')||'').indexOf('clickable')>=0 || getComputedStyle(el).cursor==='pointer')){{
          el.click(); return 'clicked-parent:'+el.tagName;
        }}
      }}
      e.click(); return 'clicked-leaf';
    }}
  }}
  return 'notfound';
}})()
'''
    return ld.eval(js)

def pick_days(ld, month_label, d1, d2):
    js = f'''
(function(){{
  var all=[].slice.call(document.querySelectorAll('*'));
  function cell(day){{
    for(var i=0;i<all.length;i++){{
      var e=all[i];
      if(e.children.length===0 && e.textContent.trim()===String(day)){{
        var p=e;
        for(var j=0;j<8 && p;j++){{
          if(p.textContent.indexOf({json.dumps(month_label)})>=0) return e;
          p=p.parentElement;
        }}
      }}
    }}
    return null;
  }}
  var s=cell({d1}), e=cell({d2});
  if(s && e){{ s.click(); e.click(); return 'picked'; }}
  return 's='+(!!s)+' e='+(!!e);
}})()
'''
    return ld.eval(js)

ld = LD()
print('before:', ld.period_text())

print('click 自定义:', click_by_text_exact(ld, '自定义'))
ld.wait(1000)

print('pick days:', pick_days(ld, '2026年7月', 1, 31))
ld.wait(800)

# confirm: try 确定 then 自定义
rc = click_by_text_exact(ld, '确定')
print('confirm 确定:', rc)
if not rc or rc.startswith('notfound'):
    rc = click_by_text_exact(ld, '自定义')
    print('confirm 自定义:', rc)
ld.wait(1500)
print('after:', ld.period_text())
ld.screenshot('out/debug/test_range.png')
ld.close()
