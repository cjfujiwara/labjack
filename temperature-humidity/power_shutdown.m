uiopen('Y:\LabJack\Logging\Temperature-Humidity\shutdown.fig',1);
hF = gcf;


times = [...
    2021 11 12 15 0 0;
    2021 11 13 07 0 0;
    2021 11 13 08 27 0;
    2021 11 13 12 05 0;
    2021 11 13 20 10 0;
    2021 11 14 08 48 0;
    2021 11 14 9 07 0;
    2021 11 14 10 30 0;
    2021 11 14 12 42 0;
    2021 11 14 15 06 0;
    2021 11 14 18 30 0;];

lbls = {'lab shutdown',
    'power off',
    'doors open',
    'small heater',
    'big heater',
    'both heater',
    'small heater',
    'both heater',
    'ac break?',
    'big heater',
    'power on'};

ypos = [22 24.5 24.3 24.1 24.5 24.5 24.3 24.1 23.5 24.5 22];

ax1 = hF.Children(3);
ax2 = hF.Children(5);

axes(ax2)
yyaxis right
ylim([0 40]);
yyaxis left
ylim([21.5 25]);
hold on
ax2.Legend.AutoUpdate='off';
for kk=1:length(lbls)
%     plot(datetime(times(kk,:)),25.2,'k*');
    plot([datetime(times(kk,:)) datetime(times(kk,:))],[21.5 25],'r--');

    yyaxis left
    text(datetime(times(kk,:)),ypos(kk),lbls{kk});
end

