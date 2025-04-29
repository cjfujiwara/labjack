function [hF,pTable,pRaw]=tempHumidityPlotter(opts)
%TEMPHUMIDITYPLOTTER Summary of this function goes here
%   Detailed explanation goes here


% fldrWeather = 'Y:\TorontoWeather';
fldrWeather = 'X:\LabJackLogs\TorontoWeather';

close all
%% Default options
if nargin == 0
   opts = struct;
end

if ~isfield(opts,'FigLabel')
   opts.FigLabel = []; 
end
FigLabel = opts.FigLabel;

%% Default Start Time
if ~isfield(opts,'t1')
    opts.t1 = [2025 04 29 00 00 00]; 
end
t1 = opts.t1;

%% Default End Time
if ~isfield(opts,'t2')
   opts.t2 = [2025 04 29 23 59 59]; 
end

t2 = opts.t2;


%% Default Averaging Time (in minutes)
if ~isfield(opts,'dt')
    opts.dt = .5;
    
%     opts.dt = 20;
end
dt = opts.dt;


%% Default Temperature Limits
if ~isfield(opts,'tlim')
   opts.tlim = 'auto'; 
%    opts.tlim = [21 26];   
end
tlim = opts.tlim;

%% Default Humidity Limits
if ~isfield(opts,'hlim')
   opts.hlim = 'auto'; 
% hlim =[20 40];              
end
hlim = opts.hlim;

%% Plot Toronto Weather?
if ~isfield(opts,'weather')
   opts.weather = 1; 
end
weather = opts.weather;

if ~isfield(opts,'dt_weather')
   opts.dt_weather = 0; 
end
dt_weather = opts.dt_weather;

% Default Channels to Plot
if ~isfield(opts,'inds')
    opts.inds =  [1 7 8];
    opts.inds = 1:8;
end
inds = opts.inds;

% Channel names
chs={'MOT Optics',...       % 1
    'XDTs / Y Lattice',...  % 2
    'Nufern',...            % 3
    'Plug / X Lattice',...  % 4
    'ALS',...               % 5
    'Z Lattice',...         % 6
    'Top Breadboard',...    % 7
    'Above Machine Cloud'}; % 8

 %% Grab the data and Average

% Load the logs
disp(' Grabbing the log files...');
tic;rawTbl=TH_loadLogs(t1,t2);tb=toc;

disp([' Log files obtained (' num2str(round(tb,2)) ' s)']);

% Resample the data using average to make plotting easier over long times
if dt > 0
    ta = now;
    fprintf(' Averaging data ...');
    pTable=retime(rawTbl,'regular','mean','timestep',minutes(dt));
    tb = now;
    disp([' done (' num2str(round((tb-ta)*60*60*24,2)) ' s)']);
else
    pTable = rawTbl;
end

% Sort the data
pTable = sortrows(pTable);

%% Grab Weather Data
if weather
   
    
    
    disp(' Grabbing the log files...');
    tic;rawTblW=loadLogsWeather(t1,t2);tb=toc;
    disp([' Log files obtained (' num2str(round(tb,2)) ' s)']);
    
    % Resample the data using average to make plotting easier over long times
    if dt_weather > 0
        ta = now;
        fprintf(' Averaging data ...');
        pTableW=retime(rawTblW,'regular','mean','timestep',minutes(dt));
        tb = now;
        disp([' done (' num2str(round((tb-ta)*60*60*24,2)) ' s)']);
    else
        pTableW = rawTblW;
    end
    pTableW = sortrows(pTableW);
    
    if datenum(t1)>datenum([2021 11 15 0 0 0])
        fprintf('grabbing historical data ... ');
        tic
        weather_toronto = load([fldrWeather filesep 'weather_toronto.mat']);
        weather_toronto = weather_toronto.weather_toronto;        
        b=toc;
        disp([num2str(b) ' seconds']);
        
        dinds = weather_toronto.time<datetime(t1);    
        weather_toronto(dinds,:)=[];
        
        pTableW = [weather_toronto;pTableW];
        
    end

    
end

%% Plot

hF=figure;
hF.Position=[50 50 1800 600];
hF.Name = 'Temperature-Humidity';
set(hF,'color','w');

hF.SizeChangedFcn = @chSize;

co=get(gca,'colororder');
co=[co; 0 0 0];

tStr = [datestr(t1,'YYYY/mm/DD HH:MM:SS') ' - ' ...
    datestr(t2,'YYYY/mm/DD HH:MM:SS')];
tBot = uicontrol('style','text','horizontalalignment','left',...
    'backgroundcolor','w','String',tStr,'fontsize',10);
tBot.Position = [1 0 tBot.Extent(3) tBot.Extent(4)];

if ~isempty(FigLabel)
    tLbl = uicontrol('style','text','horizontalalignment','left',...
        'backgroundcolor','w','String',FigLabel,'fontsize',8);
    tLbl.Position(3:4) = tLbl.Extent(3:4);
    tLbl.Position(1:2) = [1 hF.Position(4)-tLbl.Position(4)];
end


% Temperature plot
ax1 = subplot(211);

if weather
    yyaxis right
    pW = plot(pTableW.time,pTableW.temperature_C,'-','color',[.5 .5 .5 .5],'linewidth',3); 
    set(gca,'YColor',[.5 .5 .5]);
    yyaxis left
    hold on
end
    set(gca,'YColor','k');

for kk=1:length(inds)
    pT(kk)=plot(pTable.Time,pTable.([chs{inds(kk)} ' TEMP']),'-',...
        'color',co(inds(kk),:),'linewidth',1);
    hold on
end


ylim(tlim);
ylabel('temperature (C)');
xlim([datetime(t1) datetime(t2)]);
if ~weather
    leg1=legend(pT,chs{inds},'orientation','vertical',...
        'location','northeastoutside','units','pixels');
else
    leg1=legend([pW pT],[{'Toronto'}, chs{inds}],'orientation','vertical',...
        'location','northeastoutside','units','pixels');
end
set(ax1,'xgrid','on','ygrid','on','box','on','linewidth',1,...
    'fontsize',10,'units','pixels')

% Averaging
lstr=['$T_{\mathrm{avg}}$ = ' num2str(dt) ' min'];
text(5,4,lstr,'units','pixels','fontsize',13,'interpreter','latex',...
    'verticalalignment','bottom','margin',1,'backgroundcolor',[1 1 1 .7]);

% Humidity plot
ax2 = subplot(212);
if weather
    yyaxis right
    pWr = plot(pTableW.time,pTableW.humidity_percent,'-','color',[.5 .5 .5 .5],'linewidth',3); 
    set(gca,'YColor',[.5 .5 .5]);
    yyaxis left
    hold on
end
    set(gca,'YColor','k');

for kk=1:length(inds)
    pR(kk)=plot(pTable.Time,pTable.([chs{inds(kk)} ' RH']),'-',...
        'color',co(inds(kk),:),'linewidth',1);
    hold on
end
ylim(hlim);
ylabel('relative humidity (%)');
xlim([datetime(t1) datetime(t2)]);
if ~weather
    leg2=legend(pR,chs{inds},'orientation','vertical',...
        'location','northeastoutside','units','pixels');
else
    leg2=legend([pWr pR],[{'Toronto'}, chs{inds}],'orientation','vertical',...
        'location','northeastoutside','units','pixels');
end
set(ax2,'xgrid','on','ygrid','on','box','on','linewidth',1,...
    'fontsize',10,'units','pixels')
xlabel('time');

% Averaging
lstr=['$T_{\mathrm{avg}}$ = ' num2str(dt) ' min'];
text(5,4,lstr,'units','pixels','fontsize',13,'interpreter','latex',...
    'verticalalignment','bottom','margin',1,'backgroundcolor',[1 1 1 .7]);


linkaxes([ax1 ax2],'x');


    function out=loadLogsWeather(t1,t2)
        t1=floor(datenum(t1));
        t2=floor(datenum(t2));
        out=TH_readLog(makeFileNameWeather(t1));
        while floor(t1)<=floor(t2)
            str=makeFileNameWeather(t1);
            if exist(str,'file')      
                thisdata=TH_readLog(str);
                if ~isempty(thisdata)
                    out=[out;thisdata];
                end
            end
            t1=t1+1;          
        end 
    end

    function str=makeFileNameWeather(t)
       tV=datevec(t);       
       str=[fldrWeather filesep num2str(tV(1)) filesep num2str(tV(1)) '.' ...
           num2str(tV(2),'%02.f') filesep num2str(tV(2),'%02.f') '_' datestr(t,'dd') '.csv'];
    end

    function pos = axsize(fig,ax,ind)
        W = fig.Position(3);
        H = fig.Position(4);
        
        lgap = 70;
        rgap = 220;
        tgap = 40;
        bgap = 50;
        vgap = 40;
        
        w = W - lgap - rgap;
        h = 0.5*(H - bgap - vgap - tgap);
        try
            switch ind
                case 1
                    ax.Position = [lgap bgap w h];
                case 2
                    ax.Position = [lgap bgap+h+vgap w h];
            end
        end
    end

    function chSize(hdl,evt)
       axsize(hdl,ax1,2);
       axsize(hdl,ax2,1);
        leg2.Position(1) = ax2.Position(1) + ax2.Position(3) + 40;
        leg2.Position(2) = ax2.Position(2) + ax2.Position(4) - leg2.Position(4);
        leg1.Position(1) = ax2.Position(1) + ax2.Position(3) + 40;
        leg1.Position(2) = ax1.Position(2) + ax1.Position(4) - leg1.Position(4);

       if exist('tLbl','var')
            tLbl.Position(1:2) = [1 hF.Position(4)-tLbl.Position(4)]; 
       end
    end
       
chSize(hF)
end


