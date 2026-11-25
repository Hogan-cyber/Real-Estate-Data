import React, {createContext, useContext, useEffect, useMemo, useRef, useState} from 'react';
import {Button, DataComponent, DataTable, Dropdown, EvidenceChart, Section, SortableItem, SortableRegion, useDashboardTabs, useDataApp} from '../../data-app-public.jsx';
import {ReferencePeriod} from './ReferencePeriod.jsx';
import {compatibleIndicators, downloadCsv, formatValue, frequencyNames, latestCommonRows, latestRow, selectRows, recentRows, monitorEstimateDetails} from './residential-data.js';
import './residential.css';

const Context = createContext(null);
const tabs = [{id:'overview',label:'Overview'}, {id:'mortgage',label:'Mortgage',aliases:['finance']}];
const RELEASE = 'https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/';
const colors = ['var(--housing-blue)','var(--housing-orange)','var(--housing-grey)','var(--housing-gold)','var(--housing-navy)'];
const CLASSES = ['a','b','c','d','e'];
const CLASS_NAMES = {a:'A · <40 m²',b:'B · 40–69.9 m²',c:'C · 70–99.9 m²',d:'D · 100–159.9 m²',e:'E · ≥160 m²'};
const GROUP_NAMES = {Transactions:'Sales registrations',Price_Indices:'Price indices',Rent_Indices:'Rent indices',Prices:'Average prices',Rents:'Average rents',Popular_Developments:'Popular developments',Supply_Annual:'Annual supply',Mortgage_Monthly:'Bank series & legacy LR estimates',Mortgage_Registrations:'Mortgage registrations',Negative_Equity_Quarterly:'Quarterly negative equity',Money_Supply:'Money supply',HIBOR_Daily:'Daily HIBOR',Prime_Rate:'Effective Prime rate',Rates_Monthly:'Monthly average rates',Monitor_Registrations:'Monitor · Centaline registrations',Monitor_Bank:'Monitor · bank mortgages',Monitor_Registry:'Monitor · registry documents',Monitor_Nonbank:'Monitor · workbook estimates',Monitor_M3:'Monitor · money supply',Monitor_Hibor:'Monitor · daily HIBOR',Monitor_Prime:'Monitor · Prime rate'};
const col = (field,label,renderCell) => ({field,label,...(renderCell?{renderCell}:{})});
const textDate = date => date ? new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(`${date}T00:00:00Z`)) : 'No observations';
const nameOf = (catalogue,id) => catalogue.find(row=>row.metric_id===id)?.display_name || id;
const displayUnit = unit => unit==='份' ? 'agreements' : unit;
const sourceLink = row => {
  const urls=[...new Set(row.source_url.split(/;\s*|\s+\|\s+/).filter(url=>url.startsWith('https://')))];
  return <span className="res-source-links">{urls.map((url,index)=><a key={url} href={url} target="_blank" rel="noreferrer">
    {urls.length===1?row.source_name.replaceAll('香港土地注册处','Land Registry'):`Source ${index+1}`}
  </a>)}</span>;
};

function useRows(ids) { const {rows} = useContext(Context); return useMemo(()=>selectRows(rows,ids),[rows,ids.join('|')]); }
function Chart({id,title,ids,labels,description,height=310,bars=false,barHistory=false,controls,children,dataRows,scale=1,unitLabel,decimals}) {
  const {catalogue} = useContext(Context);
  const shell=useDataApp();
  const selectionKey=ids.join('|');
  const previousSelection=useRef(selectionKey);
  useEffect(()=>{
    const saved=shell.chartProps(id).visibleSeries;
    const invalidSaved=Array.isArray(saved)&&saved.length>0&&!saved.some(name=>ids.includes(name));
    if(previousSelection.current===selectionKey&&!invalidSaved) return;
    previousSelection.current=selectionKey;
    shell.chartProps(id).onVisibleSeriesChange(undefined);
    shell.chartProps(id).onZoomChange(undefined);
  },[id,selectionKey,shell.chartProps]);
  const scoped = useRows(ids);
  const selected = dataRows || scoped;
  const sourceRows = useMemo(()=>bars?latestCommonRows(selected,ids):selected,[selected,bars,ids.join('|')]);
  const unit = selected[0]?.unit || '';
  const effectiveDates = selected[0]?.frequency === 'E';
  const y = scale!==1?`Value (${unitLabel})`:unit==='fraction'?'valueShare':unit.includes('%')?'Value (%)':'value';
  const plotted = useMemo(()=>sourceRows.map(row=>({...row,[y]:row.value===null?null:row.value/scale,label:labels?.[row.metric_id] || nameOf(catalogue,row.metric_id)})),[sourceRows,y,labels,scale]);
  const available = sourceRows.some(row=>Number.isFinite(row.value));
  const legend = Object.fromEntries(ids.map(id=>[id,labels?.[id] || nameOf(catalogue,id)]));
  const spec = {type:bars?'horizontalBar':effectiveDates||barHistory?'bar':'line',x:bars?'label':'date',y,
    ...(!bars?{series:'metric_id',legend:{labels:legend}}:{}),
    colors:Object.fromEntries(ids.map((key,index)=>[key,colors[index%colors.length]])),
    stackable:false,startAtZero:bars||effectiveDates||barHistory,valueDecimals:decimals??(unit.includes('%')?5:2),
    showXAxisLabel:false,showYAxisLabel:false};
  const period = bars ? sourceRows[0]?.period : null;
  return <EvidenceChart id={id} queryId="observations" kind="chart" variant="card" title={title}
    description={description} rows={plotted} sourceRows={sourceRows} spec={spec} height={height}
    headerControls={controls}>
    <div className="res-chart-foot" data-reviewed-rows>
      {!available ? <span role="status">{bars?'No common published period in this selection.':'No published values in this selection.'}</span> :
        <span>{unitLabel||displayUnit(unit)} · {bars?period:frequencyNames[selected[0]?.frequency] || selected[0]?.frequency}
          {!bars&&sourceRows.length>0?` · ${sourceRows.reduce((first,r)=>r.date<first?r.date:first,sourceRows[0].date)} – ${sourceRows.reduce((last,r)=>r.date>last?r.date:last,sourceRows[0].date)}`:''}
          {bars&&sourceRows[0]?.frequency==='A'?` · as of ${textDate(sourceRows[0].date)}${sourceRows[0].flags?` · ${sourceRows[0].flags}`:''}`:''}</span>}
      {children}
      {effectiveDates&&<span>Each bar is a published rate-change date; no rates are inferred between dates.</span>}
    </div>
  </EvidenceChart>;
}

function Level({id,metric,title,decimals=2,latest=false,scale=1,unitLabel}) {
  const {rows,all}=useContext(Context);
  const row=latestRow(selectRows(latest?all:rows,[metric]));
  return <DataComponent id={id} queryId="observations" variant="card" kind="metric" title={title}
    sourceRows={row?[row]:[]} displayRows={row?[row]:[]}>
    <div className="res-level" data-reviewed-rows><strong>{formatValue(Number.isFinite(row?.value)?row.value/scale:null,decimals)}</strong>
      <span>{unitLabel||displayUnit(row?.unit) || 'No published value'}</span><small>{row?.frequency==='E'?`Effective ${textDate(row.date)}`:row?.frequency==='D'?textDate(row.date):row?.period || 'Selected period'}{row?.status && row.status!=='Published'?` · ${row.status}`:''}</small>
    </div>
  </DataComponent>;
}

function Tiles({items}) { return <div className="res-tiles">{items.map(item=><Level key={item.id} {...item}/>)}</div>; }
function MacroHeadline() {
  return <section className="res-macro-headline" aria-label="Latest macro and interest rates">
    <div className="res-section-heading"><h2>Macro & interest rates</h2><p>Latest published observations · independent of the chart period below</p></div>
    <Tiles items={[
      {id:'res26-prime-effective-level',metric:'monitor_prime_rate_hsbc_effective',title:'HSBC prime rate',decimals:3,latest:true},
      {id:'res26-hibor-overnight-level',metric:'monitor_hibor_overnight_daily',title:'Overnight HIBOR',decimals:5,latest:true},
      {id:'res26-hibor-1m-level',metric:'monitor_hibor_1m_daily',title:'1-month HIBOR',decimals:5,latest:true},
      {id:'res26-m3-level',metric:'monitor_m3_hkd',title:'Hong Kong dollar M3',decimals:2,scale:1000000,unitLabel:'HK$ trillion',latest:true},
    ]}/>
  </section>;
}
function Canvas({page,blocks}) {
  const rows=[];
  for(let index=0;index<blocks.length;index++) {
    const block=blocks[index];
    if(block.span===12) rows.push({id:block.id+'-row',items:[block.id]});
    else if(index+1<blocks.length&&blocks[index+1].span!==12) rows.push({id:block.id+'-row',items:[block.id,blocks[++index].id]});
    else rows.push({id:block.id+'-row',items:[block.id]});
  }
  return <SortableRegion id={`hk:${page}`} authoredRevision={5} variant="canvas" columns={12} spacing="standard" rows={rows}>
    {blocks.map(block=><SortableItem key={block.id} id={block.id} label={block.title} kind="chart" span={block.span||6}>{block.content || <Chart {...block}/>}</SortableItem>)}
  </SortableRegion>;
}

function RegionalChart() {
  const [size,setSize]=useState('a'), [measure,setMeasure]=useState('price');
  const locations=['hong_kong','kowloon','new_territories'];
  const ids=locations.map(region=>`rvd_1_${measure==='price'?'2':'1'}_class_${size}_${region}`);
  const labels=Object.fromEntries(ids.map((id,index)=>[id,['Hong Kong Island','Kowloon','New Territories'][index]]));
  return <Chart id="res26-regional" title="Average price & rent by district" ids={ids} labels={labels} bars height={300}
    description="Latest common month within the selected period. RVD transaction averages in original square-metre units. Sale prices exclude primary sales; averages are sensitive to the transaction mix."
    controls={<><Dropdown label="Measure" showLabel value={measure} onChange={setMeasure} choices={['price','rent']} choiceLabels={{price:'Average price',rent:'Average rent'}}/>
      <Dropdown label="Size class" showLabel value={size} onChange={setSize} choices={CLASSES} choiceLabels={CLASS_NAMES}/></>}/>;
}
function SizeChart() {
  const [measure,setMeasure]=useState('4');
  const ids=CLASSES.map(cls=>`rvd_1_${measure}_class_${cls}`);
  return <Chart id="res26-size" title="Price & rent indices by size" ids={ids} labels={Object.fromEntries(ids.map((id,index)=>[id,`Class ${CLASSES[index].toUpperCase()}`]))}
    description="RVD price or rent indices, 1999 = 100. A <40 m²; B 40–69.9; C 70–99.9; D 100–159.9; E ≥160."
    controls={<Dropdown label="Index" showLabel value={measure} onChange={setMeasure} choices={['4','3']} choiceLabels={{'4':'Price index','3':'Rent index'}}/>}/>;
}
function SupplyChart() {
  const [measure,setMeasure]=useState('completions');
  const ids=CLASSES.map(cls=>`rvd_${measure}_class_${cls}_${measure}`);
  return <Chart id="res26-supply" title="Annual housing supply by size" ids={ids} bars
    labels={Object.fromEntries(ids.map((id,index)=>[id,`Class ${CLASSES[index].toUpperCase()}`]))}
    description="Latest common annual reference period in the selected range. Current-year completions may be partial; the original observation notes retain the cutoff. Stock and completions are different measures."
    controls={<Dropdown label="Measure" showLabel value={measure} onChange={setMeasure} choices={['completions','stock']} choiceLabels={{completions:'Completions',stock:'Year-end stock'}}/>}>
  </Chart>;
}

function Overview() {
  const macro=[
    {id:'res26-daily-hibor',title:'Daily HIBOR fixings',span:12,content:<DailyHibor/>},
    {id:'res26-m3',title:'Money supply M3',ids:['monitor_m3_hkd','monitor_m3_total'],labels:{monitor_m3_hkd:'Hong Kong dollar',monitor_m3_total:'All currencies'},scale:1000000,unitLabel:'HK$ trillion',description:'Month-end money stock · HK$ trillion'},
    {id:'res26-prime-history',title:'HSBC prime rate',ids:['monitor_prime_rate_hsbc_effective'],labels:{monitor_prime_rate_hsbc_effective:'HSBC Prime'},description:'Published effective rates · percent per year'},
  ];
  const blocks=[
    {id:'res26-index',title:'Residential price & rent indices',span:12,height:360,ids:['rvd_1_4_all_classes','rvd_1_3_all_classes'],labels:{rvd_1_4_all_classes:'Price index',rvd_1_3_all_classes:'Rent index'},description:'RVD all-class indices, original base 1999 = 100. No rebasing or growth-rate calculation.'},
    {id:'res26-sales',title:'Residential sales registrations',ids:['hk_residential_primary_sales_count','hk_residential_secondary_sales_count'],labels:{hk_residential_primary_sales_count:'Primary sales',hk_residential_secondary_sales_count:'Secondary sales'},description:'Land Registry agreements registered each month. The registration date can lag the agreement date.'},
    {id:'res26-sales-value',title:'Sales value · primary & secondary',ids:['hk_residential_primary_sales_value','hk_residential_secondary_sales_value'],labels:{hk_residential_primary_sales_value:'Primary sales',hk_residential_secondary_sales_value:'Secondary sales'},bars:true,description:'Contract values in the latest common month. These are property sale values, not loan amounts.'},
    {id:'res26-size',title:'Indices by size',content:<SizeChart/>},
    {id:'res26-regional',title:'District comparison',content:<RegionalChart/>},
    {id:'res26-supply',title:'Annual supply',content:<SupplyChart/>},
  ];
  return <><Canvas page="overview-macro" blocks={macro}/><Section id="res26-market-heading" title="Residential market"><Tiles items={[
    {id:'res26-price-level',metric:'rvd_1_4_all_classes',title:'Residential price index',decimals:1},
    {id:'res26-rent-level',metric:'rvd_1_3_all_classes',title:'Residential rent index',decimals:1},
    {id:'res26-sales-level',metric:'hk_residential_sales_count',title:'Residential sales registrations',decimals:0},
    {id:'res26-sales-value-level',metric:'hk_residential_sales_value',title:'Residential sales value',decimals:0},
  ]}/><Canvas page="overview" blocks={blocks}/></Section><Explorer page="overview"/></>;
}

function DailyHibor() {
  const {rows}=useContext(Context);
  const tenors={overnight:'Overnight','1w':'1 week','1m':'1 month','3m':'3 months','6m':'6 months','12m':'12 months'};
  const [selected,setSelected]=useState(['overnight','1m','3m']);
  const [days,setDays]=useState('90');
  const ids=selected.map(tenor=>`monitor_hibor_${tenor}_daily`);
  const source=useMemo(()=>recentRows(selectRows(rows,ids),days),[rows,selected,days]);
  return <Chart id="res26-daily-hibor" title="Daily HIBOR fixings" ids={ids} dataRows={source} height={340}
    labels={Object.fromEntries(selected.map(tenor=>[`monitor_hibor_${tenor}_daily`,tenors[tenor]]))}
    description="Percent per year · business-day fixings"
    controls={<Dropdown label="Daily history" showLabel value={days} onChange={setDays} choices={['30','90','180','365','all']} choiceLabels={{30:'30 days',90:'90 days',180:'6 months',365:'1 year',all:'All selected dates'}}/>}>
    <fieldset className="res-tenors"><legend>HIBOR tenors</legend>{Object.entries(tenors).map(([key,label])=><label key={key}>
      <input type="checkbox" checked={selected.includes(key)} disabled={selected.length===1&&selected.includes(key)}
        onChange={()=>setSelected(old=>old.includes(key)?old.filter(value=>value!==key):[...old,key])}/>{label}</label>)}</fieldset>
  </Chart>;
}

function RegistrationTotal() {
  const {rows}=useContext(Context);
  const evidence=latestCommonRows(rows,['monitor_completed_count','monitor_offplan_count']);
  const value=evidence.length===2?evidence.reduce((sum,row)=>sum+row.value,0):null;
  return <DataComponent id="res26-monitor-total-level" queryId="observations" variant="card" kind="metric" title="Completed & off-plan registrations" sourceRows={evidence} displayRows={evidence}>
    <div className="res-level" data-reviewed-rows><strong>{formatValue(value,0)}</strong><span>registrations</span><small>{evidence[0]?.period||'No common period'} · Centaline</small></div>
  </DataComponent>;
}

function RegistrationsChart() {
  const [breakdown,setBreakdown]=useState('status');
  const ids=breakdown==='status'?['monitor_completed_count','monitor_offplan_count']:['monitor_private_completed_count','monitor_subsidized_count'];
  const labels={monitor_completed_count:'Completed',monitor_offplan_count:'Off-plan',monitor_private_completed_count:'Private residential',monitor_subsidized_count:'Subsidized housing'};
  return <Chart id="res26-monitor-registrations" title="Centaline mortgage registrations" ids={ids} labels={labels} barHistory
    description="Registrations by month. Housing types are subsets of the completed-property series."
    controls={<Dropdown label="Breakdown" showLabel value={breakdown} onChange={setBreakdown} choices={['status','housing']} choiceLabels={{status:'Completed and off-plan',housing:'Completed by housing type'}}/>}/>;
}

function ApprovalsChart() {
  const [measure,setMeasure]=useState('count');
  const ids=['primary','secondary','refinancing'].map(purpose=>`monitor_bank_approved_${purpose}_${measure}`);
  return <Chart id="res26-monitor-approvals" title="Bank approvals by purpose" ids={ids} barHistory scale={measure==='amount'?1000:1} unitLabel={measure==='amount'?'HK$ billion':'loans'}
    labels={Object.fromEntries(ids.map((id,index)=>[id,['Primary purchase','Secondary purchase','Refinancing'][index]]))}
    description={measure==='amount'?'Approved amounts · HK$ billion':'Approved loans · count'}
    controls={<Dropdown label="Measure" showLabel value={measure} onChange={setMeasure} choices={['count','amount']} choiceLabels={{count:'Loans',amount:'HK$ billion'}}/>}/>;
}

function DrawdownValue() {
  const [measure,setMeasure]=useState('total');
  const id=measure==='total'?'monitor_bank_drawn_amount':'monitor_bank_average_approved_amount';
  return <Chart id="res26-monitor-drawn-value" title={measure==='total'?'New bank drawdown value':'Average approved bank loan'} ids={[id]} labels={{[id]:measure==='total'?'Drawn down':'Average approved loan'}}
    barHistory scale={measure==='total'?1000:1} unitLabel={measure==='total'?'HK$ billion':'HK$ million per loan'}
    description={measure==='total'?'Monthly funds drawn down, including refinancing':'Average amount per newly approved loan'}
    controls={<Dropdown label="Measure" showLabel value={measure} onChange={setMeasure} choices={['total','average']} choiceLabels={{total:'Total drawn down',average:'Average approved loan'}}/>}/>;
}

function EstimateDetail() {
  const {rows,all}=useContext(Context);
  const detail=useMemo(()=>monitorEstimateDetails(rows,all),[rows,all]);
  return <details className="res-details"><summary>Estimate detail and calculation</summary>
    <div className="res-model-note">
      <p>Bank purchase estimate = (primary + secondary approval count) ÷ total approval count × drawdown count.</p>
      <p>Non-bank residual = this month's completed + off-plan registrations − the previous month's bank purchase estimate.</p>
      <p>The one-month lag and approval mix are assumptions. Completed-property registrations cover more than private housing. This is a model residual, not an observed lender count; no non-bank loan amount is supplied by this workbook.</p>
    </div>
    <DataComponent id="res26-monitor-model-detail" queryId="observations" kind="table" title="Monthly workbook estimate" sourceRows={detail.sourceRows} displayRows={detail.displayRows}
      headerControls={<Button onClick={()=>downloadCsv('monitor_monthly_estimate.csv',detail.displayRows)}>Download estimate CSV</Button>}>
      <DataTable caption="Registration month and the actual prior bank month" rows={detail.displayRows} columns={[
        col('registration_month','Registration month'),col('bank_month','Bank input month'),
        col('registrations','Completed + off-plan',v=>formatValue(v,0)),col('bank_purchase','Bank purchase estimate',v=>formatValue(v,2)),col('residual','Non-bank residual',v=>formatValue(v,2)),
      ]}/>
    </DataComponent>
  </details>;
}

function Mortgage() {
  const blocks=[
    {id:'res26-monitor-residual',title:'Non-bank residual estimate',span:12,height:340,ids:['monitor_nonbank_residual_count'],labels:{monitor_nonbank_residual_count:'Non-bank residual'},barHistory:true,
      description:'Saved workbook estimate by registration month · loans. Assumes bank drawdowns lead registration by one month; populations and loan events differ.'},
    {id:'res26-monitor-registrations',title:'Centaline mortgage registrations',content:<RegistrationsChart/>},
    {id:'res26-monitor-approvals',title:'Bank approvals by purpose',content:<ApprovalsChart/>},
    {id:'res26-monitor-drawdowns',title:'Bank applications and drawdowns',ids:['monitor_bank_applications_count','monitor_bank_drawn_count'],labels:{monitor_bank_applications_count:'Applications',monitor_bank_drawn_count:'Drawdowns'},description:'Loans per month · applications and drawdowns are different events'},
    {id:'res26-monitor-registry',title:'Land Registry mortgage documents',ids:['monitor_registry_building_count','monitor_registry_other_count','monitor_registry_discharge_count'],labels:{monitor_registry_building_count:'Building mortgages',monitor_registry_other_count:'Other charges',monitor_registry_discharge_count:'Discharges'},description:'Registered documents across property types; not a residential purchase-loan total'},
    {id:'res26-monitor-balances',title:'Outstanding bank mortgages',ids:['monitor_bank_outstanding_amount'],labels:{monitor_bank_outstanding_amount:'Outstanding'},scale:1000,unitLabel:'HK$ billion',description:'Month-end outstanding balances · HK$ billion'},
    {id:'res26-monitor-drawn-value',title:'New bank drawdown value',content:<DrawdownValue/>},
  ];
  return <><div className="res-section-heading"><h2>Mortgage</h2><p>Registrations, bank activity and the workbook estimate</p></div>
    <div className="res-tiles"><RegistrationTotal/>
      <Level id="res26-monitor-drawn-level" metric="monitor_bank_drawn_count" title="Bank drawdowns" decimals={0}/>
      <Level id="res26-monitor-purchase-level" metric="monitor_bank_purchase_drawn_count_estimate" title="Estimated bank purchase drawdowns"/>
      <Level id="res26-monitor-residual-level" metric="monitor_nonbank_residual_count" title="Non-bank residual estimate"/>
    </div>
    <Canvas page="mortgage-monitor" blocks={blocks}/><EstimateDetail/>
    <details className="res-details"><summary>Additional bank risk · quarterly negative equity</summary><Canvas page="mortgage-risk" blocks={[
      {id:'res26-negative-count',title:'Negative-equity mortgages',ids:['hk_negative_equity_count'],labels:{hk_negative_equity_count:'Loans'},description:'Quarter-end bank first-mortgage positions'},
      {id:'res26-negative-amount',title:'Negative-equity outstanding balance',ids:['hk_negative_equity_amount'],labels:{hk_negative_equity_amount:'Outstanding'},description:'Quarter-end loan balance, not the loss amount'},
    ]}/></details>
    <Explorer page="mortgage"/>
  </>;
}

function Explorer({page}) {
  const {catalogue,rows}=useContext(Context);
  const list=useMemo(()=>catalogue.filter(row=>row.page===page && !(row.metric_id.startsWith('hk_hibor_') && row.frequency==='M')),[catalogue,page]);
  const [group,setGroup]=useState('all');
  const [selected,setSelected]=useState(page==='mortgage'?'hk_mortgage_outstanding':'rvd_1_4_all_classes');
  const [comparison,setComparison]=useState('none');
  const filtered=list.filter(row=>group==='all'||row.group===group);
  const chosen=filtered.some(row=>row.metric_id===selected)?selected:filtered[0]?.metric_id;
  const info=filtered.find(row=>row.metric_id===chosen);
  const compatible=compatibleIndicators(list,chosen);
  const other=compatible.some(row=>row.metric_id===comparison)?comparison:'none';
  const ids=[chosen,...(other==='none'?[]:[other])].filter(Boolean);
  const evidence=selectRows(rows,ids);
  const controls=<><Dropdown label="Category" showLabel value={group} onChange={setGroup} choices={['all',...new Set(list.map(row=>row.group))]} choiceLabels={{all:'All categories',...GROUP_NAMES}}/>
    <Dropdown label="Indicator" showLabel searchable value={chosen} onChange={setSelected} choices={filtered.map(row=>row.metric_id)} formatChoice={id=>`${nameOf(list,id)} · ${id}`}/>
    <Dropdown label="Compare" showLabel searchable value={other} onChange={setComparison} choices={['none',...compatible.map(row=>row.metric_id)]} formatChoice={id=>id==='none'?'None':nameOf(list,id)}/></>;
  const filteredCatalogue=filtered.map(row=>{
    const within=selectRows(rows,[row.metric_id]);
    return {...row,selected_observations:within.filter(r=>r.value!==null).length};
  });
  return <Section id={`res26-${page}-explore-heading`} title={`Explore ${page==='mortgage'?'mortgage':'market & macro'} indicators`} filters={controls}>
    <p className="res-definition" data-reviewed-rows>{info?.description}</p>
    <Chart id={`res26-${page}-explorer-chart`} title={info?.display_name||'Indicator history'} ids={ids} description="Compare choices share the exact source unit and frequency. Values are filtered by the reference period and remain unchanged. All indicator IDs are available below."/>
    <details className="res-details"><summary>Selected observations · {evidence.length.toLocaleString()} records</summary>
      <DataComponent id={`res26-${page}-observations`} queryId="observations" kind="table" title="Selected observations" sourceRows={evidence} displayRows={evidence}
        headerControls={<Button onClick={()=>downloadCsv('hk_selected_observations.csv',evidence)}>Download selection CSV</Button>}>
        <DataTable caption="Selected observations in the chosen date range" rows={evidence} columns={[
          col('period','Period'),col('metric_name','Indicator',(_,r)=>nameOf(catalogue,r.metric_id)),col('value','Value',v=>formatValue(v,4)),col('unit','Unit',displayUnit),col('frequency','Frequency',v=>frequencyNames[v]),
          col('status','Status'),col('flags','Flags'),col('source_name','Source',(_,row)=>sourceLink(row)),
        ]}/>
      </DataComponent>
    </details>
    <details className="res-details"><summary>Indicator names & definitions · {filtered.length} indicators</summary>
      <DataComponent id={`res26-${page}-catalogue`} queryId="catalogue" kind="table" title="Indicator dictionary" sourceRows={filtered} displayRows={filteredCatalogue}>
        <DataTable caption="Indicator names and original units" rows={filteredCatalogue} rowKey="metric_id" onRowSelect={row=>setSelected(row.metric_id)} rowActionLabel={row=>`Show ${row.display_name}`} columns={[
          col('metric_id','Indicator ID'),col('display_name','Name'),col('unit','Unit',displayUnit),col('frequency','Frequency',v=>frequencyNames[v]),
          col('selected_observations','Values in selected range'),col('description','Definition'),
        ]}/>
      </DataComponent>
    </details>
  </Section>;
}

function DatasetFooter() {
  const {snapshot}=useDataApp();
  const downloads=snapshot.dataset.downloadBase||RELEASE;
  const names={'HK_Residential_Data.xlsx':'Excel','observations.csv':'CSV','observations.parquet':'Parquet','observations.sqlite':'SQLite','INDICATORS.md':'All indicator definitions','collection_status.json':'Collection status'};
  const files=snapshot.dataset.downloadFiles||Object.keys(names).filter(name=>name!=='INDICATORS.md');
  return <footer className="res-footer">
    <div data-reviewed-rows>{snapshot.dataset.indicators} indicators · {snapshot.dataset.observations.toLocaleString()} observations · {textDate(snapshot.dataset.startDate)} – {textDate(snapshot.dataset.endDate)}</div>
    <div className="res-downloads"><span>Full dataset:</span>{files.map(file=><a key={file} href={downloads+file}>{names[file]}</a>)}{!snapshot.dataset.downloadFiles&&<a href="https://github.com/Hogan-cyber/Real-Estate-Data/blob/residential-data/INDICATORS.md" target="_blank" rel="noreferrer">All indicator definitions</a>}</div>
    <details><summary>Dataset update & source coverage</summary><div data-reviewed-rows>
      <p>Dataset prepared {new Date(snapshot.generatedAt).toLocaleString('en-GB',{timeZone:'Asia/Hong_Kong'})} HKT. Collection is scheduled daily at 18:00 HKT; actual execution may be delayed. Each indicator keeps its own reference period.</p>
      {snapshot.monitor?.commit&&<><p>Monitor workbook checked {new Date(snapshot.monitor.source_checked_at).toLocaleString('en-GB',{timeZone:'Asia/Hong_Kong'})} HKT. Imported status: {snapshot.monitor.upstream_status}. Individual source periods are shown below.</p>
        <table className="res-coverage-table"><thead><tr><th>Source group</th><th>First period</th><th>Latest period</th></tr></thead><tbody>{Object.entries(snapshot.monitor.coverage||{}).map(([key,item])=><tr key={key}><td>{{registrations:'Centaline',bank:'Bank mortgages',registry:'Land Registry',m3:'M3',prime:'HSBC Prime (effective)',hibor:'Daily HIBOR',nonbank:'Workbook estimates'}[key]}</td><td>{item.first}</td><td>{item.last}</td></tr>)}</tbody></table>
        <a href={`https://github.com/Hogan-cyber/HK-Mortgage-Monitor/tree/${snapshot.monitor.commit}`} target="_blank" rel="noreferrer">Exact source workbook revision</a></>}
      {(snapshot.refresh?.warnings||[]).map(note=><p key={note}>{note}</p>)}
      {(snapshot.refresh?.errors||[]).map((note,index)=><p key={index}>{typeof note==='string'?note:JSON.stringify(note)}</p>)}
      <a href={snapshot.dataset.url} target="_blank" rel="noreferrer">Exact dataset used by this dashboard</a>
    </div></details>
  </footer>;
}

export function DashboardContent() {
  const {snapshot,queries,filters}=useDataApp();
  const {activeTabId}=useDashboardTabs(tabs);
  const all=queries.observations.rows;
  const rows=useMemo(()=>{
    const [start,end=start]=String(filters.date||snapshot.filters[0].defaultValue).split('..');
    return start==='all'?all:all.filter(row=>row.date>=start&&row.date<=end);
  },[all,filters.date,snapshot.filters]);
  const value=useMemo(()=>({rows,all,catalogue:queries.catalogue.rows}),[rows,all,queries.catalogue.rows]);
  return <Context.Provider value={value}><article className="residential-page">
    <h1 className="res-sr-only">Hong Kong residential property dashboard</h1>
    {snapshot.refresh?.errors?.length>0&&<p className="res-model-note" role="status" data-reviewed-rows>Latest collection was unsuccessful. The last valid published data is retained. See Dataset update & source coverage below for details.</p>}
    {activeTabId==='overview'&&<MacroHeadline/>}
    <ReferencePeriod/>
    {snapshot.monitor?.coverage&&<div className="res-coverage-strip" data-reviewed-rows><span>Centaline <strong>{snapshot.monitor.coverage.registrations?.last}</strong></span><span>Bank mortgages <strong>{snapshot.monitor.coverage.bank?.last}</strong></span><span>Daily HIBOR <strong>{snapshot.monitor.coverage.hibor?.last}</strong></span></div>}
    {activeTabId==='mortgage'?<Mortgage/>:<Overview/>}
    <DatasetFooter/>
  </article></Context.Provider>;
}
