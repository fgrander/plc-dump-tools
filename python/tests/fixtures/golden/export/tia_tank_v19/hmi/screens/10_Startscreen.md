---
name: 10_Startscreen
device: HMI_RT_5
texts: {}
objects:
- {name: Bar_1, type: Bar, tag_bindings: [tankLevel]}
- {name: Bar_2, type: Bar, tag_bindings: [bottleLevel]}
- {name: Bar_3, type: Bar, tag_bindings: [HMI_bottleLevel1]}
- {name: Bar_4, type: Bar, tag_bindings: [HMI_bottleLevel2]}
- {name: Bar_5, type: Bar, tag_bindings: [HMI_bottleLevel3]}
- {name: Button_1, type: Button}
- {name: Button_10, type: Button}
- {name: Button_11, type: Button}
- {name: Button_12, type: Button}
- {name: Button_2, type: Button}
- {name: Button_3, type: Button}
- {name: Button_4, type: Button}
- {name: Button_5, type: Button}
- {name: Button_6, type: Button}
- {name: Button_7, type: Button}
- {name: Button_8, type: Button}
- {name: Button_9, type: Button}
- {name: D6_Pilotlight_Green, type: GraphicIOField, tag_bindings: [stateRunning]}
- {name: D6_Pilotlight_Red, type: GraphicIOField, tag_bindings: [stateError]}
- {name: Graphic view_1, type: GraphicView}
- {name: Graphic view_12, type: GraphicView}
- {name: Graphic view_13, type: GraphicView}
- {name: Graphic view_14, type: GraphicView}
- {name: Graphic view_2, type: GraphicView}
- {name: Graphic view_3, type: GraphicView}
- {name: Graphic view_4, type: GraphicView}
- {name: Graphic view_5, type: GraphicView}
- {name: Graphic view_6, type: GraphicView}
- {name: Graphic view_7, type: GraphicView}
- {name: Graphic view_8, type: GraphicView}
- {name: I/O field_1, type: IOField, tag_bindings: [qrCodeReceived]}
- {name: I/O field_2, type: IOField, tag_bindings: [alarmIncoming]}
- {name: Line_1, type: Line}
- {name: Line_2, type: Line}
- {name: Line_3, type: Line}
- {name: Line_4, type: Line}
- {name: Rectangle_1, type: Rectangle}
- {name: Rectangle_2, type: Rectangle}
- {name: Rectangle_3, type: Rectangle}
- {name: Rectangle_4, type: Rectangle}
- {name: Rectangle_5, type: Rectangle}
- {name: Rectangle_6, type: Rectangle}
- {name: Rectangle_7, type: Rectangle}
- {name: Rectangle_8, type: Rectangle}
- {name: Text field_1, type: TextField}
- {name: Text field_10, type: TextField}
- {name: Text field_11, type: TextField}
- {name: Text field_12, type: TextField}
- {name: Text field_13, type: TextField}
- {name: Text field_14, type: TextField}
- {name: Text field_15, type: TextField}
- {name: Text field_16, type: TextField}
- {name: Text field_17, type: TextField}
- {name: Text field_18, type: TextField}
- {name: Text field_19, type: TextField}
- {name: Text field_2, type: TextField}
- {name: Text field_3, type: TextField}
- {name: Text field_4, type: TextField}
- {name: Text field_5, type: TextField}
- {name: Text field_6, type: TextField}
- {name: Text field_7, type: TextField}
- {name: Text field_8, type: TextField}
- {name: Text field_9, type: TextField}
- {name: bottle finished 1, type: GraphicView}
- {name: bottle finished 1_1, type: GraphicView}
- {name: bottle finished 1_2, type: GraphicView}
- {name: bottle finished 1_3, type: GraphicView}
- {name: bottle finished 1_4, type: GraphicView}
- {name: bottle finished 1_5, type: GraphicView}
- {name: bottle finished 1_6, type: GraphicView}
- {name: ioKPI, type: IOField, tag_bindings: [tankTemperature]}
- {name: ioKPI_1, type: IOField, tag_bindings: [tankLevel]}
- {name: ioKPI_2, type: IOField, tag_bindings: [bottlesProduced]}
- {name: ioKPI_3, type: IOField, tag_bindings: [bootleNumberFaulty]}
- {name: ioKPI_4, type: IOField, tag_bindings: [bottleLevel]}
- {name: ioKPI_6, type: IOField, tag_bindings: [tankPressure]}
- {name: ioKPI_7, type: IOField, tag_bindings: [batchID]}
---

# Screen 10_Startscreen

Device: `HMI_RT_5`

| Object | Type | Tags |
|---|---|---|
| Bar_1 | Bar | tankLevel |
| Bar_2 | Bar | bottleLevel |
| Bar_3 | Bar | HMI_bottleLevel1 |
| Bar_4 | Bar | HMI_bottleLevel2 |
| Bar_5 | Bar | HMI_bottleLevel3 |
| Button_1 | Button |  |
| Button_10 | Button |  |
| Button_11 | Button |  |
| Button_12 | Button |  |
| Button_2 | Button |  |
| Button_3 | Button |  |
| Button_4 | Button |  |
| Button_5 | Button |  |
| Button_6 | Button |  |
| Button_7 | Button |  |
| Button_8 | Button |  |
| Button_9 | Button |  |
| D6_Pilotlight_Green | GraphicIOField | stateRunning |
| D6_Pilotlight_Red | GraphicIOField | stateError |
| Graphic view_1 | GraphicView |  |
| Graphic view_12 | GraphicView |  |
| Graphic view_13 | GraphicView |  |
| Graphic view_14 | GraphicView |  |
| Graphic view_2 | GraphicView |  |
| Graphic view_3 | GraphicView |  |
| Graphic view_4 | GraphicView |  |
| Graphic view_5 | GraphicView |  |
| Graphic view_6 | GraphicView |  |
| Graphic view_7 | GraphicView |  |
| Graphic view_8 | GraphicView |  |
| I/O field_1 | IOField | qrCodeReceived |
| I/O field_2 | IOField | alarmIncoming |
| Line_1 | Line |  |
| Line_2 | Line |  |
| Line_3 | Line |  |
| Line_4 | Line |  |
| Rectangle_1 | Rectangle |  |
| Rectangle_2 | Rectangle |  |
| Rectangle_3 | Rectangle |  |
| Rectangle_4 | Rectangle |  |
| Rectangle_5 | Rectangle |  |
| Rectangle_6 | Rectangle |  |
| Rectangle_7 | Rectangle |  |
| Rectangle_8 | Rectangle |  |
| Text field_1 | TextField |  |
| Text field_10 | TextField |  |
| Text field_11 | TextField |  |
| Text field_12 | TextField |  |
| Text field_13 | TextField |  |
| Text field_14 | TextField |  |
| Text field_15 | TextField |  |
| Text field_16 | TextField |  |
| Text field_17 | TextField |  |
| Text field_18 | TextField |  |
| Text field_19 | TextField |  |
| Text field_2 | TextField |  |
| Text field_3 | TextField |  |
| Text field_4 | TextField |  |
| Text field_5 | TextField |  |
| Text field_6 | TextField |  |
| Text field_7 | TextField |  |
| Text field_8 | TextField |  |
| Text field_9 | TextField |  |
| bottle finished 1 | GraphicView |  |
| bottle finished 1_1 | GraphicView |  |
| bottle finished 1_2 | GraphicView |  |
| bottle finished 1_3 | GraphicView |  |
| bottle finished 1_4 | GraphicView |  |
| bottle finished 1_5 | GraphicView |  |
| bottle finished 1_6 | GraphicView |  |
| ioKPI | IOField | tankTemperature |
| ioKPI_1 | IOField | tankLevel |
| ioKPI_2 | IOField | bottlesProduced |
| ioKPI_3 | IOField | bootleNumberFaulty |
| ioKPI_4 | IOField | bottleLevel |
| ioKPI_6 | IOField | tankPressure |
| ioKPI_7 | IOField | batchID |
