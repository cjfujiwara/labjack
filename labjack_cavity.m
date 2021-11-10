function labjack_cavity
%% Load Dependencies

disp(repmat('-',1,60));disp([mfilename '.m']);disp(repmat('-',1,60)); 

% Add all subdirectories for this m file
curpath = fileparts(mfilename('fullpath'));
addpath(curpath);addpath(genpath(curpath))  

%% Load previous instances
guiname = 'labjack_cavity';

% Find any instances of the GUI and bring it to focus, this is tof avoid
% restarting the GUI which may leave the shutter open.
h = findall(0,'tag','GUI');
for ii=1:length(h)
    
    if isequal(h(ii).Name,guiname)        
        warning(['Cavity GUI instance detected.  Bringing into focus. ' ...
            ' If you want to start a new instance, close the original cavity GUI.']); 
       figure(h(ii));
       return;
    end    
end

%% Default Settings
npt = struct;

% Labckjack default ip address
npt.myip            = '192.168.1.124';

% Labjack handle is empty by default
npt.handle          = 0;

% Digital trigger channel
npt.TRIGGER_NAME    = 'DIO0'; % Which channel to use for trigger

% Analog input channels
npt.names           = ['cavity','scan'];    % Input names
npt.ScanListNames   = {'AIN0','AIN1'} ;     % Input channels
npt.numAddresses    = length(npt.ScanListNames);

% Analog output channels
npt.OUT             = 'DAC0';       % Output channel
npt.outName         = 'DAC0';       % Output channel

% Default Acquisition Parameters
npt.scanRate        = 20e3;         % Data sampling rate [Hz]
npt.numScans        = 5500;         % Number of scans to take 
npt.scansPerRead    = npt.numScans; % Scan per read

npt.delay           = 0.1;          % Delay time between acquisitions [s]
npt.timeout         = 1;            % Timeout before stream is aborted [s]

% Default lock set point 
npt.dfSet           = -.140;        % [GHz]

% Default Lock Parameters
npt.tLim            = [100 240];    % [ms] time limits to find peaks
npt.hysteresis      = 0.01;         % [GHz] hystersis window
npt.dv              = 1;            % [mV] step size of lock

% Default lock mode
npt.LockMode        = 4;

% Manual write mode
npt.ManualWrite     = 0;
npt.ManualWriteStep = 0;

% Acquisition is default off
npt.isConnected     = 0;
npt.doAcq           = 0;
npt.doLock          = 0;

% Maximum time to remember old lock point [s]
Nhis = 600;

% Log Directory root
logRoot = 'Y:\LabJack\CavityLock\Logs';

%% Load LJM
try
    % Make the LJM .NET assembly visible in MATLAB
    ljmAsm = NET.addAssembly('LabJack.LJM');
    % Creating an object to nested class LabJack.LJM.CONSTANTS
    t = ljmAsm.AssemblyHandle.GetType('LabJack.LJM+CONSTANTS');
    LJM_CONSTANTS = System.Activator.CreateInstance(t);
catch ME2
    warning(['Unable to load LJM NET assembly.  ' ...
        'Have you installed all the packages given by Labjack?']);
end

%% Figure and Panels

% Initialize the primary figure
hF=figure;
clf
set(hF,'Color','w','units','pixels','Name',guiname,...
    'toolbar','figure','Tag','GUI','CloseRequestFcn',@closeGUI,...
    'NumberTitle','off','Position',[50 50 800 500],...
    'SizeChangedFcn',@figResize);


% Callback for when the GUI is requested to be closed.
    function closeGUI(fig,~)
        disp('Closing labjack cavity GUI...');
        try              
            if npt.isConnected~=0
               npt = disconnect(npt);
            end
        catch ME
            warning('Error when closing GUI.');
            warning(ME.message);
        end
        delete(fig);                % Delete the figure
    end

% Connect panel
hpCon = uipanel('parent',hF,'units','pixels','backgroundcolor','w',...
    'title','connect','position',[1 hF.Position(4)-75 200 75]);

% Acquisition panel
hpAcq = uipanel('parent',hF,'units','pixels','backgroundcolor','w',...
    'title','acquisition','position',[1 hF.Position(4)-215 200 140]);

% Lock Panel
hpLock = uipanel('parent',hF,'units','pixels','backgroundcolor','w',...
    'title','lock','position',[1 hF.Position(4)-515 200 300]);

% Main plot panel
hpAx = uipanel('parent',hF,'units','pixels','backgroundcolor','w');
hpAx.Position = [hpCon.Position(3) 1 hF.Position(3)-hpCon.Position(3) hF.Position(4)];

% Status string
tStatus = uicontrol('parent',hpAx,'style','text','string','blah',...
    'backgroundcolor','w','horizontalalignment','left');
tStatus.Position =[1 1 250 20];

% Timing string
tTiming = uicontrol('parent',hpAx,'style','text','string','blah',...
    'backgroundcolor','w','horizontalalignment','left');
tTiming.Position =[1 20 200 20];

% Label string
tLabel = uicontrol('parent',hpAx,'style','text','string','DISCONNECTED',...
    'backgroundcolor','w','horizontalalignment','right','fontsize',14,...
    'fontweight','bold');
tLabel.Position =[hpAx.Position(3)-175 3 170 20];

    function updateLabel(npt)
        if ~npt.isConnected
            set(tLabel,'String','DISCONNECTED',...
                'Foregroundcolor',[200 0 0]/255);
        end        
        
        if npt.isConnected && ~npt.doLock && ~npt.doAcq
            set(tLabel,'String','CONNECTED',...
                'Foregroundcolor',[0 150 0]/255);
        end
        
        if npt.isConnected && ~npt.doLock && npt.doAcq
            set(tLabel,'String','ACQUIRING',...
                'Foregroundcolor',[0    0.4470    0.7410]);
        end

        if npt.isConnected && npt.doLock && npt.doAcq
            set(tLabel,'String','LOCK ENGAGED',...
                'Foregroundcolor','r');
        end

    end

% Resize Function
    function figResize(fig,~)
       if fig.Position(3) > 400 && fig.Position(4) > 400        
           hpCon.Position(2) = hF.Position(4) - hpCon.Position(4);
           hpAcq.Position(2) = hpCon.Position(2) - hpAcq.Position(4);
           hpLock.Position(2) = hpAcq.Position(2) - hpLock.Position(4);           
           hpAx.Position(3:4) = [hF.Position(3)-hpCon.Position(3) hF.Position(4)];
           tLabel.Position(1) = hpAx.Position(3)-tLabel.Position(3)-5;
       end
    end

%% Main plots

ax1 = subplot(3,1,[1 2],'Parent',hpAx);
set(ax1,'box','on','linewidth',1,'xgrid','on','ygrid','on','fontsize',8);
xlabel('time (ms)');
ylabel('voltage (V)');
hold on

% Data plot
pData = plot(1,1,'k-');

% Peak A plot
pPeakA = plot(1,1,'rx','Visible','off');

% FSR A Plot
pFSRA = plot(1,1,'r-','Visible','off');
tFSRA = text(1,1,'a','units','data','verticalalignment','bottom',...
    'horizontalalignment','center','fontsize',8,'color','r',...
    'Visible','off');

% Peak B Plot
pPeakB = plot(1,1,'bx','Visible','off');

% FSR B Plot
pFSRB = plot(1,1,'b-','Visible','off');
tFSRB = text(1,1,'a','units','data','verticalalignment','bottom',...
    'horizontalalignment','center','fontsize',8,'color','b',...
    'Visible','off');

% Peak Delta Plot
pDelta = plot(1,1,'k-','Visible','off');

% Delta t text
tDelta = text(1,1,'a','units','data','verticalalignment','bottom',...
    'horizontalalignment','center','fontsize',8,'color','k',...
    'Visible','off');

yyaxis right
ylabel('ramp voltage (V)');

% Ramp Plot
sData = plot(1,1,'-');                  
% Low Time limit Plot
pLim1 = plot(npt.tLim(1)*[1 1],[0 10],'g--','linewidth',2);
% High Time limit plot
pLim2 = plot(npt.tLim(2)*[1 1],[0 10],'g--','linewidth',2);

% History plot
ax2 = subplot(3,1,3,'Parent',hpAx);

pHis = plot(now,nan,'k-');
datetick('x',13);
set(ax2,'box','on','linewidth',1,'xgrid','on','ygrid','on','fontsize',8);
xlabel('time');
ylabel('detuning (GHz)');

yyaxis right
pVOut = plot(now,nan,'r-');
ylabel('output (V)');


% disableDefaultInteractivity(ax1)
% disableDefaultInteractivity(ax2)

%% Connection and Acquisition

% Connect Button
ttStr = 'Connect';
hb_connect=uicontrol(hpCon,'style','pushbutton','string','connect','Fontsize',10,...
    'Backgroundcolor','w','Callback',@doConnect,...
    'ToolTipString',ttStr,'backgroundcolor',[80 200 120]/255,'enable','on');
hb_connect.Position = [2 hpCon.Position(4)-40 70 20];

% Disconnect Button
ttStr = 'Disconnect';
hb_disconnect=uicontrol(hpCon,'style','pushbutton','string','disconnect','Fontsize',10,...
    'Backgroundcolor','w','Position',[81 1 80 20],'Callback',@doDisconnect,...
    'ToolTipString',ttStr,'backgroundcolor',[255 102 120]/255,...
    'enable','off');
hb_disconnect.Position =hb_connect.Position + [71 0 25 0];

% Ethernet IP address
tIP = uitable('parent',hpCon,'RowName',{'IP '},'ColumnName',{},...
    'fontsize',10,'data',{npt.myip},'ColumnWidth',{120},'ColumnEditable',true);
tIP.Position(3:4)=tIP.Extent(3:4);
tIP.Position(1:2) = [2 hb_connect.Position(2) - 30];

    function doConnect(~,~)
        disp('Connecting to labjack');
        npt=connect(npt);
        
        hb_connect.Enable       = 'off';
        hb_disconnect.Enable    = 'on';        
        hb_startAcq.Enable      = 'on';
        hb_stopAcq.Enable       = 'off';
        hb_force.Enable         = 'on';
    end

    function doDisconnect(~,~)
        disp('Disconnecting from labjack');
        npt=disconnect(npt);
        
        hb_connect.Enable       = 'on';
        hb_disconnect.Enable    = 'off';        
        hb_startAcq.Enable      = 'off';
        hb_stopAcq.Enable       = 'off';
        hb_force.Enable         = 'off';
        
        tOut.Enable             = 'off';
        hb_v_down_10.Enable     = 'off';
        hb_v_down_1.Enable      = 'off';
        hb_v_up_1.Enable        = 'off';
        hb_v_up_10.Enable       = 'off';
        tLockB.Enable           = 'off';
    end

%% Acquisition

% force acquisition button
ttStr = 'Force Acq';
hb_force=uicontrol(hpAcq,'style','pushbutton','string','force','Fontsize',10,...
    'Backgroundcolor',[255,255,255]/255,'Callback',@force,...
    'ToolTipString',ttStr,'enable','off');
hb_force.Position = [2 hpAcq.Position(4)-40 50 20];

% start acquisition button
ttStr = 'Start Acq';
hb_startAcq=uicontrol(hpAcq,'style','pushbutton','string','start','Fontsize',10,...
    'Backgroundcolor','w','Callback',@startAcq,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[85 205 252]/255);
hb_startAcq.Position = hb_force.Position + [52 0 0 0];

% stp[ acquisition button
ttStr = 'Stop acquisition';
hb_stopAcq=uicontrol(hpAcq,'style','pushbutton','string','stop','Fontsize',10,...
    'Backgroundcolor','w','Position',[244 1 40 20],'Callback',@stopAcq,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[247, 168, 184]/255);
hb_stopAcq.Position = hb_startAcq.Position + [52 0 0 0];

% acquisition settings panel
n = {'Rate (Hz)', 'Num Scans','Delay (s)','scans/read'};
tAcq = uitable('parent',hpAcq,'RowName',n,'ColumnName',{},...
    'fontsize',10,'data',[npt.scanRate; npt.numScans; npt.delay;npt.scansPerRead],...
    'ColumnWidth',{50},'ColumnEditable',true,'CellEditCallback',@tacqcb);
tAcq.Position(3:4)  =  tAcq.Extent(3:4);
tAcq.Position(1:2)  = [2 hb_stopAcq.Position(2) - 90];

    function tacqcb(a,b)
        i = b.Indices(1,1);
        switch i
            case 1
                fOld = b.PreviousData;
                fNew = b.NewData;                
                if isnumeric(fNew) && fNew > 10 && fNew < 50001
                   a.Data(i)    = round(fNew);
                   npt.scanRate = round(fNew);
                else
                    a.Data(i)       = fOld;
                    warning('invalid scan rate');                    
                end
            case 2
                NOld = b.PreviousData;
                NNew = b.NewData;                
                if isnumeric(NNew) && NNew > 10 && NNew < 20001
                   a.Data(i)    = round(NNew);
                   npt.numScans = round(NNew);
                else
                    a.Data(i)       = NOld;
                    warning('invalid number of scans');                    
                end
            case 3
                TOld = b.PreviousData;
                TNew = b.NewData;                
                if isnumeric(TNew) && TNew > 0 && TNew < 11
                   a.Data(i)    = TNew;
                   npt.delay    = TNew;
                   timer_labjack.Period = npt.delay;
                else
                    a.Data(i)       = TOld;
                    warning('invalid delay time');                    
                end    
            case 4
                NOld = b.PreviousData;
                NNew = b.NewData;                
                if isnumeric(NNew) && NNew > 10 && NNew <= npt.numScans
                   a.Data(i)    = round(NNew);
                   npt.scansPerRead = round(NNew);
                else
                    a.Data(i)       = NOld;
                    warning('invalid scans per read');                    
                end                
                
        end
    end

% Force acquisition callback
    function force(~,~)
        disp([datestr(now,13) ' Forcing acquisition.']);
        npt=configureStream(npt);
        grabData
    end

% start acquisition callback
    function startAcq(~,~)
        disp([datestr(now,13) ' Starting acquisition.']);
        npt.doAcq               = 1;
        hb_force.Enable         = 'off';
        hb_startAcq.Enable      = 'off';
        hb_stopAcq.Enable       = 'on';
        hb_startLock.Enable     = 'on';
        hb_stopLock.Enable      = 'off';
        tAcq.Enable             = 'off';
        
        tOut.Enable             = 'on';
        hb_v_down_10.Enable     = 'on';
        hb_v_down_1.Enable      = 'on';
        hb_v_up_1.Enable        = 'on';
        hb_v_up_10.Enable       = 'on';
        tLockB.Enable           = 'on';
        
        set(pHis,'XData',now','YData',nan);
        set(pVOut,'XData',now','YData',nan);


        npt.doLock              = 0;
        drawnow;   
        
        npt=configureStream(npt);
        configureDeviceForTriggeredStream(npt);
        configureLJMForTriggeredStream;
        drawnow;
        timer_labjack.Period = npt.delay;
        
        updateLabel(npt);
        start(timer_labjack);    
    end

% stop acquisition callback
    function stopAcq(~,~)
        disp([datestr(now,13) ' Stopping acquisition.']);
        npt.doAcq               = 0;
        hb_force.Enable         = 'on';
        hb_startAcq.Enable      = 'on';
        hb_stopAcq.Enable       = 'off';
        hb_startLock.Enable     = 'off';
        hb_stopLock.Enable      = 'off';
        tAcq.Enable             = 'on';
        
        tOut.Enable             = 'off';
        hb_v_down_10.Enable     = 'off';
        hb_v_down_1.Enable      = 'off';
        hb_v_up_1.Enable        = 'off';
        hb_v_up_10.Enable       = 'off';
        tLockB.Enable           = 'off';   
        
        npt.doLock              = 0;        
        drawnow;                
        updateLabel(npt);

        stop(timer_labjack);            
    end
%% Lock Graphics and Callbacks

% start lock button
ttStr = 'Start lock';
hb_startLock=uicontrol(hpLock,'style','pushbutton','string','start lock','Fontsize',10,...
    'Backgroundcolor','w','Callback',@startLock,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[137 207 240]/255);
hb_startLock.Position = [2 hpLock.Position(4)-40 75 20];

% stop lock button
ttStr = 'Stop lock';
hb_stopLock=uicontrol(hpLock,'style','pushbutton','string','stop lock','Fontsize',10,...
    'Backgroundcolor','w','Position',[366 1 80 20],'Callback',@stopLock,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[255,165,0]/255);
hb_stopLock.Position = hb_startLock.Position + [77 0 0 0];

% Down 10 mV
ttstr='-10 mV';
hb_v_down_10=uicontrol(hpLock,'Style','pushbutton','units','pixels',...
    'backgroundcolor','w','String',[char(10094) char(10094)],'fontsize',8,...
    'callback',{@chOut, -10},'ToolTipString',ttstr,'enable','off');
hb_v_down_10.Position(3:4)=[15 25];
hb_v_down_10.Position(1:2) = [2 hb_startLock.Position(2)-30];

% Down 1 mV
ttstr='-1 mV';
hb_v_down_1=uicontrol(hpLock,'Style','pushbutton','units','pixels',...
    'backgroundcolor','w','String',[char(10094)],'fontsize',8,...
    'callback',{@chOut, -1},'ToolTipString',ttstr,'enable','off');
hb_v_down_1.Position(3:4)=[15 25];
hb_v_down_1.Position(1:2) = hb_v_down_10.Position(1:2) + [15 0];

% Up 1 mV
ttstr='+1 mV';
hb_v_up_1=uicontrol(hpLock,'Style','pushbutton','units','pixels',...
    'backgroundcolor','w','String',[char(10095)],'fontsize',8,...
    'callback',{@chOut, 1},'ToolTipString',ttstr,'enable','off');
hb_v_up_1.Position(3:4)=[15 25];
hb_v_up_1.Position(1:2) = hb_v_down_1.Position(1:2) + [15 0];

% Up 10 mV
ttstr='+10 mV';
hb_v_up_10=uicontrol(hpLock,'Style','pushbutton','units','pixels',...
    'backgroundcolor','w','String',[char(10095) char(10095)],'fontsize',8,...
    'callback',{@chOut, 10},'ToolTipString',ttstr,'enable','off');
hb_v_up_10.Position(3:4)=[15 25];
hb_v_up_10.Position(1:2) = hb_v_up_1.Position(1:2) + [15 0];

% Output voltage
tOut = uitable('parent',hpLock,'RowName',{'V0 (V)'},'ColumnName',{},...
    'fontsize',10,'data',[3.123],...
    'ColumnWidth',{49},'ColumnEditable',true,'enable','off');
tOut.Position(3:4)  =  tOut.Extent(3:4);
tOut.Position(1:2)  = [hb_v_up_10.Position(1)+15+2 hb_stopLock.Position(2) - 30];

% Time Set
tdF = uitable('parent',hpLock,'RowName',{'df set (GHz)'},'ColumnName',{},...
    'fontsize',10,'data',[npt.dfSet],...
    'ColumnWidth',{55},'ColumnEditable',true,'columnformat',{'numeric'},...
    'CellEditCallback',@chLockPoint);
tdF.Position(3:4)  =  tdF.Extent(3:4);
tdF.Position(1:2)  = [2 tOut.Position(2) - 30];

    function chLockPoint(a,b)
        if isnumeric(b.NewData) && (b.NewData>-1.5 || b.NewData<1.5)
            npt.dfSet = tdF.Data;
        else
            a.Data = b.PreviousData;
        end
        
    end

% Measured Parameters
n = {'df npt (GHz)','dT npt (ms)','FSR npt (ms)'};
tLockB = uitable('parent',hpLock,'RowName',n,'ColumnName',{},...
    'fontsize',10,'data',[10; 10; 10],...
    'ColumnWidth',{55},'ColumnEditable',false,'enable','off');
tLockB.Position(3:4)  =  tLockB.Extent(3:4);
tLockB.Position(1:2)  = [2 tdF.Position(2) - tLockB.Extent(4)-10];

% Lock Settings
n = {'T start (ms)', 'T stop (ms)','hyst. (GHz)','step (mV)'};
tLockA = uitable('parent',hpLock,'RowName',n,'ColumnName',{},...
    'fontsize',10,'data',[npt.tLim(1); npt.tLim(2); npt.hysteresis; npt.dv],...
    'ColumnWidth',{55},'ColumnEditable',true,'CellEditCallback',@chLockA);
tLockA.Position(3:4)  =  tLockA.Extent(3:4);
tLockA.Position(1:2)  = [2 tLockB.Position(2) - 90];

    function chLockA(a,b)
        i = b.Indices(1,1);
        switch i
            case 1
                t1New   = b.NewData;
                t1Old   = b.PreviousData;
                t2      = a.Data(2);
                if isnumeric(t1New) && t1New > 0 && t1New < 1000 && t1New < t2
                    a.Data(1)   = t1New; 
                    npt.tLim(1) = t1New;
                    pLim1.XData = [1 1]*t1New;
                else
                    a.Data(1) = t1Old; 
                    warning('invalid time limit');
                end
            case 2
                t2New   = b.NewData;
                t2Old   = b.PreviousData;
                t1      = a.Data(1);
                if isnumeric(t2New) && t2New > 0 && t2New < 1000 && t2New > t1
                    a.Data(2)   = t2New; 
                    npt.tLim(2) = t2New;
                    pLim2.XData = [1 1]*t2New;
                else
                    a.Data(2) = t2Old; 
                    warning('invalid time limit');
                end
            case 3
                tHNew   = b.NewData;
                tHOld   = b.PreviousData;
                if isnumeric(tHNew) && tHNew > 0 && tHNew < 5
                    a.Data(3)       = tHNew;
                    npt.hysteresis  = tHNew;
                else
                    a.Data(3)       = tHOld;
                    warning('invalid hysteresis time');
                end
            case 4
                vNew   = b.NewData;
                vOld   = b.PreviousData;
                if isnumeric(vNew) && vNew > 0 && vNew < 50
                    a.Data(4)   = vNew;
                    npt.dv      = vNew;
                else
                    a.Data(4)   = vOld;
                    warning('invalid voltage step');
                end               
                
        end
      
    end


    function startLock(~,~)
        disp([datestr(now,13) ' Engaging lock.']);
        
        npt.doLock = 1;
        hb_startLock.Enable     =' off';
        hb_stopLock.Enable      = 'on';    
        
        tOut.Enable             = 'off';
        hb_v_down_10.Enable     = 'off';
        hb_v_down_1.Enable      = 'off';
        hb_v_up_1.Enable        = 'off';
        hb_v_up_10.Enable       = 'off';
        updateLabel(npt);

        if npt.LockMode ==4
           npt.FSR = range(pFSRA.XData);
        end
        
        % Setup and call eReadName to read a value.
        [ljmError, value] = LabJack.LJM.eReadName(npt.handle, npt.OUT, 0);        
        npt.OUT_VALUE_INIT = value;           
        
        
    end

    function stopLock(~,~)
        disp([datestr(now,13) ' Stopping lock.']);
        npt.doLock = 0;
        
        hb_startLock.Enable     = 'on';
        hb_stopLock.Enable      = 'off';  

        tOut.Enable             = 'on';
        hb_v_down_10.Enable     = 'on';
        hb_v_down_1.Enable      = 'on';
        hb_v_up_1.Enable        = 'on';
        hb_v_up_10.Enable       = 'on';
        updateLabel(npt);

    end

    function chOut(~,~,v)
        % Read Current output voltage              
        npt.ManualWrite     = 1;
        npt.ManualWriteStep = v;
    end



%% Timr Objects

% Initialize the trig checker
timer_labjack=timer('name','Labjack Cavity Timer','Period',npt.delay,...
    'ExecutionMode','FixedSpacing','TimerFcn',@grabData);

    function grabData(~,~)
        
        if npt.ManualWrite
            [ljmError, value] = LabJack.LJM.eReadName(npt.handle, npt.OUT, 0);
        
            % Update internal recording of voltage
            npt.OUT_VALUE = value;        
            tOut.Data = value; 

            v = npt.ManualWriteStep;
            
            newVal = value + v*1e-3;

            if newVal > 0 && newVal < 5
                tStatus.String = ['Writing ' num2str(newVal) ' ... '];
                LabJack.LJM.eWriteName(npt.handle,npt.OUT, newVal);
                tStatus.String = ['Writing ' num2str(newVal) ' ... done'];
            end

            % Read Current output voltage
            [ljmError, value] = LabJack.LJM.eReadName(npt.handle, npt.OUT, 0);

            % Update internal recording of voltage
            npt.OUT_VALUE = value;        
            tOut.Data = value;  
            
            npt.ManualWrite = 0;
            npt.ManualWriteStep = 0;
        end
        
        tStatus.String = 'configuring ... ';
        configureDeviceForTriggeredStream(npt);
        configureLJMForTriggeredStream;
        pause(0.01);
        
        tic;
        tStatus.String = [tStatus.String ' streaming ...' ];
        [yNew,isGood] = performStream;
        
        if isGood
            tNew = 1e3*(0:(size(yNew,2)-1))/npt.scanRate;
            updateData(tNew,yNew);
            t2=toc;
        else
            t2=toc;
            tStatus.String = ['ERROR (' num2str(round(t2,3)) ' s)'];
            warning('error on data capture'); 
        end
        
        
    end

%% Data Stuff
    function updateData(t,y)     
        tStatus.String = [tStatus.String ' plotting ... '];

        
        % Update plots
        set(pData,'XData',t,'YData',y(1,:));
        set(sData,'XData',t,'YData',y(2,:));
        set(pLim1,'Ydata',[0 max(y(2,:))]);
        set(pLim2,'Ydata',[0 max(y(2,:))]);
        set(ax1,'XLim',[min(t) max(t)]);
        set(ax1,'YLim',[0 1.2]);      


        % Restrict Peak search to time limits        
        i1 = t > npt.tLim(1);
        i2 = t < npt.tLim(2);
        i = i1 & i2;
        
        % Find Peaks
        [yPeak,Tp]=findpeaks(y(1,i),t(i),'MinPeakHeight',0.5,'MinPeakProminence',.4);        
        
        % Read Current output voltage
        try
            [ljmError, value] = LabJack.LJM.eReadName(npt.handle, npt.OUT, 0);
        catch err
            warning('error on grab value of output');
            value = nan;
        end
           
        % Update internal recording of voltage
        npt.OUT_VALUE = value;        
        tOut.Data = value;   
        
        % Update if you find four peaks
        if length(yPeak) == 4            
            % Sort in descending order of height
            [yPeak,inds]=sort(yPeak,'descend');
            Tp=Tp(inds);                

            % Two tallest peaks are peak A
            TpA = Tp(1:2);yA = yPeak(1:2);

            % Next two tallest peaks are peak B
            TpB = Tp(3:4);yB = yPeak(3:4);

            % Sort them by time
            [TpA,ia]=sort(TpA);yA=yA(ia);[TpB,ib]=sort(TpB);yB=yB(ib);

            % Get the FSR
            FSR_A = range(TpA);FSR_B = range(TpB);

            % Find peak separatin
            Tdelta = TpB(1)-TpA(1);        
            
            % Update Data Tables
            tLockB.Data(1) = (Tdelta/FSR_B)*1.5;
            tLockB.Data(2) = Tdelta;
            tLockB.Data(3) = FSR_B;

            % Update separation between peaks
            set(pDelta,'XData',[TpA(1) TpB(1)],'YData',[1 1]*mean([yA(1) yB(1)]),'Visible','on');
            set(tDelta,'String',[num2str(round(Tdelta,3)) ' ms'],'Visible','on');  
            tDelta.Position(1:2) = [mean(pDelta.XData) mean(pDelta.YData)];

            % Update peak identification markers
            set(pPeakA,'XData',TpA,'YData',yA,'Visible','on');
            set(pPeakB,'XData',TpB,'YData',yB,'Visible','on');

            % Update FSR A Plot and Text
            set(pFSRA,'XData',TpA,'YData',min(yA)*[1 1],'Visible','on')  
            set(tFSRA,'String',[num2str(round(FSR_A,3)) ' ms'],'Visible','on');
            tFSRA.Position(1:2) = [mean(pFSRA.XData) mean(pFSRA.YData)];

            % Update FSR B Plot and Text
            set(pFSRB,'XData',TpB,'YData',min(yB)*[1 1],'Visible','on')
            set(tFSRB,'String',[num2str(round(FSR_B,3)) ' ms'],'Visible','on');
            tFSRB.Position(1:2) = [mean(pFSRB.XData) mean(pFSRB.YData)];           
            
            
            if length(pHis.XData) == Nhis
                tHis = circshift(pHis.XData,-1);
                tHis(end) = now;

                yHis = circshift(pHis.YData,-1);
                yHis(end) = tLockB.Data(1);
                
                yVOut = circshift(pVOut.YData,-1);
                yVOut(end) = npt.OUT_VALUE;
            else               
                tHis = [pHis.XData now];
                yHis = [pHis.YData tLockB.Data(1)];
                yVOut = [pVOut.YData npt.OUT_VALUE];
            end            
            
            set(pHis,'XData',tHis,'YData',yHis);
            set(pVOut,'XData',tHis,'YData',yVOut);

            set(ax2,'XLim',[min(tHis) max(tHis)]);
            datetick('x','HH:MM');

            if npt.doLock && npt.LockMode == 4
                df_meas = (Tdelta/FSR_B)*1.5;   % Measured detuning
                df_set  = npt.dfSet;            % Setpoint detuning

               % Only engage lock if FSR is close to original
               if abs(npt.FSR-FSR_B)/npt.FSR < 0.05
                   % Log Current Status
                try                          
                    [fname,isFile] = getLogFile(logRoot);    

                        T = timetable(...
                            datetime(datevec(now)),...
                            round(FSR_B,2),...
                            round(Tdelta,2),...
                            round(npt.OUT_VALUE,4));
                        T.Properties.VariableNames = ...
                            {'fsr meas (ms)','dt meas (ms)',' vout (V)'};
                        if ~isFile
                            writetimetable(T,fname,'Delimiter',',');
                        else
                            writetimetable(T,fname,'Delimiter',',','WriteVariableNames',false,...
                                'WriteMode','append');
                        end                            
                   catch ME
                       warning('unable to log data');
                   end                        

                   newVal = value;  % New voltage is the old one
                   doWrite = 0;     % Don't write a new voltage by default

                   % Is the value sufficiently above the set point?
%                    disp(df_meas-df_set)
                   if df_meas>(df_set+abs(npt.hysteresis))
                      % Increment by 1mV and enable writing
                      newVal = value - npt.dv*1e-3; 
                      doWrite = 1;
                   end

                  % Is the value sufficiently below the set point?
                   if df_meas<(df_set-abs(npt.hysteresis))
                       % Increment by 1mV and enable writing
                        newVal = value + npt.dv*1e-3;
                        doWrite = 1;
                   end

                   % Write the new voltage if necessary
                   if doWrite
                       % Check if new voltage is within capture range
                       if abs(newVal - npt.OUT_VALUE_INIT)<0.2
                           try
                            LabJack.LJM.eWriteName(npt.handle, ...
                                npt.OUT, newVal);
                           catch err2
                               newVal = nan;
                               warning('error on piezo write');
                           end
                           tStatus.String = ['Writing ' num2str(newVal)];
                       else
                           warning('Unable to write value outside of voltage limits');
                       end                           
                   end
               end    
            end
        else
            pPeakA.Visible='off';
            pPeakB.Visible='off';
            pDelta.Visible='off';
            tDelta.Visible='off';
            pFSRA.Visible='off';
            tFSRA.Visible='off';
            pFSRB.Visible='off';
            tFSRB.Visible='off';
            
            % Update Data Tables
            tLockB.Data(1) = nan;
            tLockB.Data(2) = nan;
            tLockB.Data(3) = nan;
        end        
       
        
        drawnow;
        tStatus.String = [tStatus.String ' done! '];

    end


%% Labjack Functions


function [Y_ALL,isGood] = performStream
    tStart = now;
    
    % Time for each read
    sleepTime = double(npt.scansPerRead)/double(npt.scanRate);

    % Initializing Bookkeeeping variables
    totScans = 0;
    totSkip = 0;
    i = 0;
    dataAll = {};
    isGood = 1;    
    Y_ALL=[];

    % Wait until trigger is low
    tLevel = 0;
    tic
    while tLevel == 0
%         [~,tLevel]=LabJack.LJM.eReadName(npt.handle,'USER_RAM0_I32',0);
        [~,tLevel]=LabJack.LJM.eReadName(npt.handle,'DIO0',0);
        pause(0.01);        
    end
    t2=toc;
%     tStatus.String = [' trigger wait ' num2str(round(1e3*t2,1)) ' ms'];
        
    % Begin the Stream
    [ljm_err, npt.scanRate] = LabJack.LJM.eStreamStart(npt.handle, int32(npt.scansPerRead), ...
        int32(npt.numAddresses), npt.aScanList, int32(npt.scanRate));
    if ~isequal(string(ljm_err),'NOERROR')        
        warning('error detected on stream start')
    end
    
    tic;
    pause(sleepTime + 0.01); 
    while (totScans < npt.numScans) && isGood                     
        try
            % Read data in buffer
            [~, devScanBL, ljmScanBL] = LabJack.LJM.eStreamRead( ...
                npt.handle, npt.aData, 0, 0);
            
            % Update scans
            totScans = totScans+npt.scansPerRead;

            % Update skipped measurements
            curSkip = sum(double(npt.aData)==-9999.0);
            totSkip = totSkip + curSkip;
            
            % Increment stream read
            i = i+1;        
            
            % Append Data
            dataAll{i}=double(npt.aData);  
            
            % Wait if more data to be had
            if  totScans < npt.numScans
                pause(sleepTime)
            end            

        catch ME   
            if isequal(char(ME.ExceptionObject.LJMError),...
                    'NO_SCANS_RETURNED')                
                t3 = toc;
                if t3>npt.timeout
                    warning(' Timeout exceeded.');                        
                    npt=disconnect(npt);
                    npt=connect(npt);
                    npt=configureStream(npt);
                    try
                        LabJack.LJM.eStreamStop(npt.handle);
                    end
                    isGood = 0;
                end  
            else
                isGood=0;
            end
        end         
    end
    
    if isGood        
        try
            LabJack.LJM.eStreamStop(npt.handle);
        end        
        t3 = toc;       % Stream Duration
        tEnd = now;     % Total Time

         tTiming.String = [... 
             '(' num2str(1e3*t2,'%03.f') ' ms, ' ...
             num2str(1e3*t3,'%03.f') ' ms, ' ...
             num2str(1e3*(tEnd-tStart)*24*60*60,'%03.f') ' ms)'];
        drawnow;

        Y_ALL=[];
        for kk=1:length(dataAll)
            Y = dataAll{kk};
            Y = reshape(Y,[npt.numAddresses length(Y)/npt.numAddresses]);
            Y_ALL = [Y_ALL Y];
        end    
    end
end


function npt = connect(npt)
    try
        % Ethernet Connect
        fprintf([datestr(now,13) ' Connecting to labjack ... ']);
        [ljmError, npt.handle] = LabJack.LJM.OpenS('T7', 'ETHERNET', npt.myip, npt.handle);        
% USB
%         [ljmError, npt.handle] = LabJack.LJM.OpenS('T7', 'USB', 'ANY', npt.handle);        
        disp( ' done');
        try
            [ljmError] = LabJack.LJM.eStreamStop(npt.handle);
        end
        npt.isConnected = 1;
        showDeviceInfo(npt.handle);  
        updateLabel(npt);
    end
end

function npt=disconnect(npt)
    disp('Disconnecting');
    LabJack.LJM.Close(npt.handle);
    npt.handle=0;
    npt.isConnected = 0;
    updateLabel(npt)
end

    function configureLJMForTriggeredStream
        LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_SCANS_RETURN,...
            LJM_CONSTANTS.STREAM_SCANS_RETURN_ALL_OR_NONE);
%         LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_SCANS_RETURN,...
%             1);        
%         LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_RECEIVE_TIMEOUT_MS,...
%             0);  
        LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_RECEIVE_TIMEOUT_MS,...
           30);  
    end

function configureDeviceForTriggeredStream(npt)
%     """Configure the device to wait for a trigger before beginning stream.
% 
%     @para handle: The device handle
%     @type handle: int
%     @para triggerName: The name of the channel that will trigger stream to start
%     @type triggerName: str
%     """

    LabJack.LJM.eWriteName(npt.handle, 'STREAM_TRIGGER_INDEX', 2000);

    % Clear any previous settings on triggerName's Extended Feature registers    
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_ENABLE'], 0);
%https://labjack.com/support/datasheets/t-series/digital-io/extended-features/pulse-width
    % EF_IDEX --> 5 pulse width in
    % EF_CONFIG_A is continues or one shot (??)
    
    % 5 enables a rising or falling edge to trigger stream
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 5);
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 12);

% This works
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 5);
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_CONFIG_A'], 0);

% This works
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 3);    
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_CONFIG_A'], 1);


    % This is the best one? 2021/11/05
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 4);    
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_CONFIG_A'], 1);
    
    % Enable
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_ENABLE'], 1);
end


function npt = configureStream(npt)
    % Configure the strea
    T = npt.numScans * npt.numAddresses /npt.scanRate;

    disp(['nScan=' num2str(npt.numScans) ',' ...
        'nAddr=' num2str(npt.numAddresses) ',' ...
        'rScan=' num2str(npt.scanRate) ' Hz,' ...
        'scansperRead= ' num2str(npt.scansPerRead) ...
        ' ==> ' num2str(round(T,1)) ' seconds']);
    t1 = now;
    fprintf('Configuring data stream ...');

    % Scan list names to stream.
    aScanListNames = NET.createArray('System.String', npt.numAddresses);    
    for kk=1:npt.numAddresses
        aScanListNames(kk) = npt.ScanListNames{kk};
    end
    npt.aScanListNames = aScanListNames;

    % Create Scan List
    npt.aScanList = NET.createArray('System.Int32', npt.numAddresses);
    % Dummy array for aTypes parameter
    npt.aTypes = NET.createArray('System.Int32', npt.numAddresses);
    LabJack.LJM.NamesToAddresses(npt.numAddresses, npt.aScanListNames, ...
        npt.aScanList, npt.aTypes);

    % Setup the scan Rate and ata
%     npt.scansPerRead = min([int32(npt.scanRate/2) int32(npt.numScans)]);
%     npt.scansPerRead = npt.numScans;
%     npt.scansPerRead = 100;

    % Stream reads will be stored in aData. Needs to be at least
    % numAddresses*scansPerRead in size.
    npt.aData = NET.createArray('System.Double', int32(npt.numAddresses*npt.scansPerRead));

    LabJack.LJM.eWriteName(npt.handle, 'STREAM_TRIGGER_INDEX', 0); % Trigger
    LabJack.LJM.eWriteName(npt.handle, 'STREAM_CLOCK_SOURCE', 0);  % Timing

    % All negative channels are single-ended, AIN0 and AIN1 ranges are
    % +/-10 V, stream settling is 0 (default) and stream resolution index
    % is 0 (default).
    numFrames = 4;
    aNames = NET.createArray('System.String', numFrames);
    aNames(1) = 'AIN_ALL_NEGATIVE_CH';
    aNames(2) = 'AIN0_RANGE';
    aNames(3) = 'STREAM_SETTLING_US';
    aNames(4) = 'STREAM_RESOLUTION_INDEX';
    aValues = NET.createArray('System.Double', numFrames);
    aValues(1) = LJM_CONSTANTS.GND;
    aValues(2) = 10.0;
    aValues(3) = 0;
    aValues(4) = 0;

    % Write the analog inputs' negative channels (when applicable), ranges
    % stream settling time and stream resolution configuration.
    LabJack.LJM.eWriteNames(npt.handle, numFrames, aNames, aValues, -1);
    
    t2 = now;
    disp([' done (' num2str(round((t2-t1)*60*60*24,3)) 's)']);

end


end

function [fileDay,fileexist] = getLogFile(logRoot)

mydatevec = datevec(now);

dirYear  = [logRoot filesep num2str(mydatevec(1))];
dirMonth = [dirYear filesep num2str(mydatevec(1)) '.' sprintf('%2.2d',mydatevec(2))];
fileDay  = [dirMonth filesep sprintf('%2.2d',mydatevec(2)) '_' sprintf('%2.2d',mydatevec(3)) '.csv'];

if ~exist(logRoot,'dir')
   warning('No data server found.');
   fileDay = [];
   return;  
end

if ~exist(dirYear,'dir')
   mkdir(dirYear); 
end

if ~exist(dirMonth,'dir')
    mkdir(dirMonth);
end

fileexist=exist(fileDay,'file');


end
