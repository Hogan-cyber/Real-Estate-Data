import React, {createContext, useContext, useEffect, useMemo, useRef, useState} from 'react';
import {Button, DataComponent, DataTable, Dropdown, EvidenceChart, Section, SortableItem, SortableRegion, useDashboardTabs, useDataApp} from '../../data-app-public.jsx';
import {ReferencePeriod} from './ReferencePeriod.jsx';
import {compatibleIndicators, downloadCsv, formatValue, frequencyNames, latestCommonRows, latestRow, selectRows} from './residential-data.js';
import './residential.css';

const Context = createContext(null);
const tabs = [{id:'overview',label:'Overview'}, {id:'mortgage',label:'Mortgage',aliases:['finance']}];
const RELEASE = 'https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/';
const METHOD = 'https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md';
const colors = ['var(--housing-blue)','var(--housing-orange)','var(--housing-grey)','var(--housing-gold)','var(--housing-navy)'];
const CLASSES = ['a','b','c','d','e'];
const CLASS_NAMES = {a:'A · <40 m²',b:'B · 40–69.9 m²',c:'C · 70–99.9 m²',d:'D · 100–159.9 m²',e:'E · ≥160 m²'};
const GROUP_NAMES = {Transactions:'Sales registrations',Price_Indices:'Price indices',Rent_Indices:'Rent indices',Prices:'Average prices',Rents:'Average rents',Popular_Developments:'Popular developments',Supply_Annual:'Annual supply',Mortgage_Monthly:'Monthly mortgages & estimates',Mortgage_Registrations:'Mortgage registrations',Negative_Equity_Quarterly:'Quarterly negative equity',Money_Supply:'Money supply',HIBOR_Daily:'Daily HIBOR',Prime_Rate:'Effective Prime rate',Rates_Monthly:'Monthly average rates'};
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
function Chart({id,title,ids,labels,description,height=310,bars=false,controls,children}) {
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
  const selected = useRows(ids);
  const sourceRows = useMemo(()=>bars?latestCommonRows(selected,ids):selected,[selected,bars,ids.join('|')]);
  const unit = selected[0]?.unit || '';
  const effectiveDates = selected[0]?.frequency === 'E';
  const y = unit==='fraction'?'valueShare':unit.includes('%')?'Value (%)':'value';
  const plotted = useMemo(()=>sourceRows.map(row=>({...row,[y]:row.value,label:labels?.[row.metric_id] || nameOf(catalogue,row.metric_id)})),[sourceRows,y,labels]);
  const available = sourceRows.some(row=>Number.isFinite(row.value));
  const legend = Object.fromEntries(ids.map(id=>[id,labels?.[id] || nameOf(catalogue,id)]));
  const spec = {type:bars?'horizontalBar':effectiveDates?'bar':'line',x:bars?'label':'date',y,
    ...(!bars?{series:'metric_id',legend:{labels:legend}}:{}),
    colors:Object.fromEntries(ids.map((key,index)=>[key,colors[index%colors.length]])),
    stackable:false,startAtZero:bars||effectiveDates,valueDecimals:unit.includes('%')?3:2,
    showXAxisLabel:false,showYAxisLabel:false};
  const period = bars ? sourceRows[0]?.period : null;
  return <EvidenceChart id={id} queryId="observations" kind="chart" variant="card" title={title}
    description={description} rows={plotted} sourceRows={sourceRows} spec={spec} height={height}
    headerControls={controls}>
    <div className="res-chart-foot" data-reviewed-rows>
      {!available ? <span role="status">{bars?'No common published period in this selection.':'No published values in this selection.'}</span> :
        <span>{displayUnit(unit)} · {bars?period:frequencyNames[selected[0]?.frequency] || selected[0]?.frequency}
          {bars&&sourceRows[0]?.frequency==='A'?` · as of ${textDate(sourceRows[0].date)}${sourceRows[0].flags?` · ${sourceRows[0].flags}`:''}`:''}</span>}
      {children}
      {effectiveDates&&<span>Each bar is a published rate-change date; no rates are inferred between dates.</span>}
    </div>
  </EvidenceChart>;
}

function Level({id,metric,title,decimals=2,latest=false}) {
  const {rows,all}=useContext(Context);
  const row=latestRow(selectRows(latest?all:rows,[metric]));
  return <DataComponent id={id} queryId="observations" variant="card" kind="metric" title={title}
    sourceRows={row?[row]:[]} displayRows={row?[row]:[]}>
    <div className="res-level" data-reviewed-rows><strong>{formatValue(row?.value,decimals)}</strong>
      <span>{displayUnit(row?.unit) || 'No published value'}</span><small>{row?.frequency==='E'?`Effective ${textDate(row.date)}`:row?.frequency==='D'?textDate(row.date):row?.period || 'Selected period'}{row?.status && row.status!=='Published'?` · ${row.status}`:''}</small>
    </div>
  </DataComponent>;
}

function Tiles({items}) { return <div className="res-tiles">{items.map(item=><Level key={item.id} {...item}/>)}</div>; }
function MacroHeadline() {
  return <section className="res-macro-headline" aria-label="Latest macro and interest rates">
    <div className="res-section-heading"><h2>Macro & interest rates</h2><p>Latest published observations · independent of the chart period below</p></div>
    <Tiles items={[
      {id:'res26-prime-effective-level',metric:'hk_prime_rate_hsbc_effective',title:'HSBC Prime · effective rate',decimals:3,latest:true},
      {id:'res26-hibor-1m-level',metric:'hk_hibor_1m_daily',title:'1-month HIBOR · daily fixing',decimals:5,latest:true},
      {id:'res26-hibor-3m-level',metric:'hk_hibor_3m_daily',title:'3-month HIBOR · daily fixing',decimals:5,latest:true},
      {id:'res26-m3-level',metric:'hk_m3_hkd',title:'Hong Kong dollar M3',decimals:0,latest:true},
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
  return <SortableRegion id={`hk:${page}`} authoredRevision={4} variant="canvas" columns={12} spacing="standard" rows={rows}>
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
    {id:'res26-daily-hibor',title:'Daily HIBOR fixings',ids:['hk_hibor_1m_daily','hk_hibor_3m_daily'],labels:{hk_hibor_1m_daily:'1-month HIBOR',hk_hibor_3m_daily:'3-month HIBOR'},description:'Published daily fixings in percent per annum. Original daily observations; no monthly averaging.'},
    {id:'res26-m3',title:'Money supply · Hong Kong dollar M3',ids:['hk_m3_hkd'],labels:{hk_m3_hkd:'HK dollar M3'},description:'HKMA month-end money stock, HKD million. Original published levels.'},
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

const modelCount=['hk_residential_mortgage_count_estimate','hk_bank_mortgage_purchase_drawn_count_estimate','hk_money_lender_mortgage_count_estimate'];
const modelAmount=['hk_residential_mortgage_amount_estimate','hk_bank_mortgage_purchase_drawn_amount_estimate','hk_money_lender_mortgage_amount_estimate'];
const modelLabels=ids=>Object.fromEntries(ids.map((id,index)=>[id,['Residential total · estimate','Bank ex-refinance · estimate','Money-lender residual · estimate'][index]]));
function ModelChart({amount=false}) {
  return <Chart id={`res26-model-${amount?'amount':'count'}`} title={amount?'Mortgage amounts · existing scenarios':'Mortgage counts · existing estimates'} ids={amount?modelAmount:modelCount} labels={modelLabels(amount?modelAmount:modelCount)}
    description="The dataset's existing estimates are plotted without recalculation. The residual is not an observed pure money-lender series. Negative residuals are retained."/>;
}
function Mortgage() {
  const counts=['hk_mortgage_approved_primary_count','hk_mortgage_approved_secondary_count','hk_mortgage_approved_refinancing_count'];
  const amounts=counts.map(id=>id.replace('_count','_amount'));
  const approvalLabels=ids=>Object.fromEntries(ids.map((id,index)=>[id,['Primary purchase','Secondary purchase','Refinancing'][index]]));
  const banks=[
    {id:'res26-bank-count',title:'Bank approvals & drawdowns · count',ids:['hk_mortgage_approved_count','hk_mortgage_drawn_count'],labels:{hk_mortgage_approved_count:'Approved',hk_mortgage_drawn_count:'Drawn'},description:'HKMA residential mortgage survey. Approval and drawdown totals include refinancing and are not necessarily the same loans.'},
    {id:'res26-bank-amount',title:'Bank approvals & drawdowns · amount',ids:['hk_mortgage_approved_amount','hk_mortgage_drawn_amount'],labels:{hk_mortgage_approved_amount:'Approved',hk_mortgage_drawn_amount:'Drawn'},description:'Monthly flows in HKD million, including refinancing. Outstanding loan balances are a separate stock series in the indicator browser.'},
    {id:'res26-approval-count',title:'Bank approvals by purpose · count',ids:counts,labels:approvalLabels(counts),bars:true,description:'Latest common reference month for the primary, secondary and refinancing approval counts.'},
    {id:'res26-approval-amount',title:'Bank approvals by purpose · amount',ids:amounts,labels:approvalLabels(amounts),bars:true,description:'Latest common reference month for approval amounts. This breakdown describes approvals, not drawdowns.'},
    {id:'res26-lr',title:'All-property mortgage registrations',ids:['hk_all_property_mortgage_deeds_count'],labels:{hk_all_property_mortgage_deeds_count:'Mortgage / charge documents'},description:'LR items 5 + 6 across residential, non-residential and land. Documents, not unique loans; refinancing is not separately removed.'},
    {id:'res26-pricing',title:'New bank mortgages by pricing basis',ids:['hk_mortgage_pricing_blr_share','hk_mortgage_pricing_hibor_share','hk_mortgage_pricing_fixed_share','hk_mortgage_pricing_other_share'],labels:{hk_mortgage_pricing_blr_share:'Prime-linked',hk_mortgage_pricing_hibor_share:'HIBOR-linked',hk_mortgage_pricing_fixed_share:'Fixed rate',hk_mortgage_pricing_other_share:'Other'},description:'Published shares of new approved loans by pricing basis. These percentages are not mortgage interest rates.'},
  ];
  const estimates=[
    {id:'res26-model-count',title:'Existing count estimates',content:<ModelChart/>},
    {id:'res26-model-amount',title:'Existing amount scenarios',content:<ModelChart amount/>},
  ];
  const risk=[
    {id:'res26-negative-count',title:'Negative-equity mortgages · count',ids:['hk_negative_equity_count'],labels:{hk_negative_equity_count:'Negative-equity loans'},description:'HKMA quarter-end bank first-mortgage positions. Quarterly stocks are not converted to monthly originations.'},
    {id:'res26-negative-amount',title:'Negative-equity mortgages · outstanding',ids:['hk_negative_equity_amount'],labels:{hk_negative_equity_amount:'Outstanding amount'},description:'Quarter-end outstanding balance of negative-equity residential mortgages. This is not the loss amount; negative equity is not equivalent to default.'},
  ];
  return <><Tiles items={[
    {id:'res26-drawn-count-level',metric:'hk_mortgage_drawn_count',title:'Bank mortgage drawdowns',decimals:0},
    {id:'res26-drawn-amount-level',metric:'hk_mortgage_drawn_amount',title:'Bank amount drawn',decimals:0},
    {id:'res26-approved-level',metric:'hk_mortgage_approved_amount',title:'Bank amount approved',decimals:0},
    {id:'res26-delinquency-level',metric:'hk_mortgage_delinquency',title:'Mortgage delinquency · >3 months',decimals:3},
  ]}/><Canvas page="mortgage-bank" blocks={banks}/>
    <Section id="res26-estimates-heading" title="Residential total, bank & money-lender estimates">
      <div className="res-model-note" data-reviewed-rows>
        These are the estimates already published in the dataset. The residential total uses the LR residential-sales share; the bank series excludes estimated refinancing using the approval mix. The remainder is labelled a money-lender residual, but can still include bank refinancing and scope differences. Amounts assume the bank purchase average loan size. <a href={METHOD} target="_blank" rel="noreferrer">Calculation & limitations</a>
      </div><Canvas page="mortgage-estimates" blocks={estimates}/>
    </Section>
    <Section id="res26-risk-heading" title="Quarterly negative equity"><Canvas page="mortgage-risk" blocks={risk}/></Section>
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
  return <footer className="res-footer">
    <div data-reviewed-rows>{snapshot.dataset.indicators} indicators · {snapshot.dataset.observations.toLocaleString()} observations · {textDate(snapshot.dataset.startDate)} – {textDate(snapshot.dataset.endDate)}</div>
    <div className="res-downloads"><span>Full dataset:</span><a href={RELEASE+'HK_Residential_Data.xlsx'}>Excel</a><a href={RELEASE+'observations.csv'}>CSV</a><a href={RELEASE+'observations.parquet'}>Parquet</a><a href={RELEASE+'observations.sqlite'}>SQLite</a><a href="https://github.com/Hogan-cyber/Real-Estate-Data/blob/residential-data/INDICATORS.md" target="_blank" rel="noreferrer">All indicator definitions</a></div>
    <details><summary>Dataset update & source coverage</summary><div data-reviewed-rows>
      <p>Published dataset checked {new Date(snapshot.generatedAt).toLocaleString('en-GB',{timeZone:'Asia/Hong_Kong'})} HKT. Official collection runs daily at 18:00 HKT. Each indicator keeps its own reference period.</p>
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
    <MacroHeadline/>
    <ReferencePeriod/>
    {activeTabId==='mortgage'?<Mortgage/>:<Overview/>}
    <DatasetFooter/>
  </article></Context.Provider>;
}
